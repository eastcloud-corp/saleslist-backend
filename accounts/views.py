import logging
from urllib.parse import urlparse
from typing import Iterable

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, update_session_auth_hash
from django.utils import timezone
from django.conf import settings
from .serializers import LoginSerializer, UserProfileSerializer
from .models import User
from . import mfa


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _get_origin_candidates(request) -> Iterable[str]:
    origin = request.headers.get('Origin')
    referer = request.headers.get('Referer')
    for value in (origin, referer):
        if value:
            yield value


def _normalize_origin(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = urlparse(value)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    except ValueError:
        return None
    return value


def _is_origin_allowed(request) -> bool:
    if getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', False):
        return True

    allowed = set(getattr(settings, 'CORS_ALLOWED_ORIGINS', []))
    allowed.update(getattr(settings, 'CSRF_TRUSTED_ORIGINS', []))

    candidates = [_normalize_origin(candidate) for candidate in _get_origin_candidates(request)]
    candidates = [candidate for candidate in candidates if candidate]

    if not candidates:
        return True

    return any(candidate in allowed for candidate in candidates)


logger = logging.getLogger('security.auth')


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def login_view(request):
    """ログインAPI"""
    client_ip = _get_client_ip(request)
    origin_candidates = list(_get_origin_candidates(request))
    if not _is_origin_allowed(request):
        logger.warning('login.rejected.origin', extra={
            'client_ip': client_ip,
            'origins': origin_candidates,
        })
        return Response({'error': '不正なオリジンからのリクエストです'}, status=status.HTTP_403_FORBIDDEN)
    serializer = LoginSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.validated_data['user']

        try:
            pending_auth_id, _ = mfa.create_pending_auth(user)
        except mfa.MFAEmailError:
            logger.error('login.mfa_send_failed', extra={
                'client_ip': client_ip,
                'user_id': user.id,
                'user_email': user.email,
            })
            return Response({'error': '確認コードの送信に失敗しました'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info('login.mfa_pending', extra={
            'client_ip': client_ip,
            'user_id': user.id,
            'user_email': user.email,
        })

        return Response({
            'mfa_required': True,
            'pending_auth_id': pending_auth_id,
            'email': user.email,
            'expires_in': settings.MFA_TOKEN_TTL_SECONDS,
            'resend_interval': settings.MFA_RESEND_INTERVAL_SECONDS,
        }, status=status.HTTP_200_OK)

    logger.warning('login.failure', extra={
        'client_ip': client_ip,
        'errors': serializer.errors,
        'username': request.data.get('email', ''),
        'origins': origin_candidates,
    })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def mfa_resend_view(request):
    """MFA確認コードの再送API"""
    pending_auth_id = request.data.get('pending_auth_id')
    client_ip = _get_client_ip(request)

    if not pending_auth_id:
        return Response({'error': 'pending_auth_id が必要です'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        mfa.resend_token(pending_auth_id)
    except mfa.PendingAuthNotFound:
        logger.warning('mfa.resend.not_found', extra={
            'client_ip': client_ip,
            'pending_auth_id': pending_auth_id,
        })
        return Response({'error': '確認コードを再送できません。再度ログインしてください。'}, status=status.HTTP_410_GONE)
    except mfa.PendingAuthExpired:
        logger.warning('mfa.resend.expired', extra={
            'client_ip': client_ip,
            'pending_auth_id': pending_auth_id,
        })
        return Response({'error': '確認コードの有効期限が切れています。ログインからやり直してください。'}, status=status.HTTP_410_GONE)
    except mfa.ResendNotAllowed as exc:
        reason = str(exc)
        logger.warning('mfa.resend.rejected', extra={
            'client_ip': client_ip,
            'pending_auth_id': pending_auth_id,
            'reason': reason,
        })
        if reason == 'RESEND_TOO_SOON':
            return Response({'error': '確認コードの再送はしばらくお待ちください'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        return Response({'error': '確認コードの再送制限に達しています'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
    except mfa.MFAEmailError:
        logger.error('mfa.resend.send_failed', extra={
            'client_ip': client_ip,
            'pending_auth_id': pending_auth_id,
        })
        return Response({'error': '確認コードの送信に失敗しました'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    logger.info('mfa.resend.success', extra={
        'client_ip': client_ip,
        'pending_auth_id': pending_auth_id,
    })
    return Response({'message': '確認コードを再送しました'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def mfa_verify_view(request):
    """MFA確認コードの検証API"""
    pending_auth_id = request.data.get('pending_auth_id')
    token = request.data.get('token')
    client_ip = _get_client_ip(request)

    if not pending_auth_id or not token:
        return Response({'error': 'pending_auth_id と token は必須です'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        pending = mfa.verify_token(pending_auth_id, token)
    except (mfa.PendingAuthNotFound, mfa.PendingAuthExpired):
        logger.warning('mfa.verify.expired', extra={
            'client_ip': client_ip,
            'pending_auth_id': pending_auth_id,
        })
        return Response({'error': '確認コードの有効期限が切れています。ログインからやり直してください。'}, status=status.HTTP_410_GONE)
    except mfa.TokenMismatch:
        logger.warning('mfa.verify.mismatch', extra={
            'client_ip': client_ip,
            'pending_auth_id': pending_auth_id,
        })
        return Response({'error': '確認コードが一致しません'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(id=pending.get('user_id')).first()
    if not user or not user.is_active:
        logger.warning('mfa.verify.user_missing', extra={
            'client_ip': client_ip,
            'pending_auth_id': pending_auth_id,
        })
        return Response({'error': 'ユーザーが見つかりません'}, status=status.HTTP_404_NOT_FOUND)

    refresh = RefreshToken.for_user(user)
    access_token = refresh.access_token

    user.last_login_at = timezone.now()
    user.save(update_fields=['last_login_at'])

    logger.info('login.success', extra={
        'client_ip': client_ip,
        'user_id': user.id,
        'user_email': user.email,
    })

    return Response({
        'access_token': str(access_token),
        'refresh_token': str(refresh),
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role,
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """ログアウトAPI"""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                blacklist = getattr(token, 'blacklist', None)
                if callable(blacklist):
                    blacklist()
                else:
                    logger.debug('RefreshToken.blacklistが利用できないためブラックリスト処理をスキップしました。')
            except Exception as token_error:
                # ブラックリスト未使用の環境では例外が発生することがあるが、基本的には無視してよい
                logger.warning('RefreshTokenの無効化に失敗しました: %s', token_error)
        
        return Response({
            'message': 'ログアウトしました'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.exception('ログアウト処理中に例外が発生しました')
        return Response({
            'error': 'ログアウト処理でエラーが発生しました'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """現在のユーザー情報取得API"""
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def refresh_view(request):
    """トークン更新API（OpenAPI仕様準拠）"""
    refresh_token = request.data.get('refresh_token')
    client_ip = _get_client_ip(request)
    origin_candidates = list(_get_origin_candidates(request))
    if not _is_origin_allowed(request):
        logger.warning('refresh.rejected.origin', extra={
            'client_ip': client_ip,
            'origins': origin_candidates,
        })
        return Response({'error': '不正なオリジンからのリクエストです'}, status=status.HTTP_403_FORBIDDEN)

    if not refresh_token:
        logger.warning('refresh.failure.missing_token', extra={'client_ip': client_ip, 'origins': origin_candidates})
        return Response({
            'error': 'refresh_token が必要です'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        refresh = RefreshToken(refresh_token)
        access_token = refresh.access_token

        logger.info('refresh.success', extra={'client_ip': client_ip, 'origins': origin_candidates})
        return Response({
            'access_token': str(access_token),
            'refresh_token': str(refresh)
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.warning('refresh.failure.invalid_token', extra={'client_ip': client_ip, 'error': str(e), 'origins': origin_candidates})
        return Response({
            'error': 'トークンの更新に失敗しました'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_user_view(request):
    """ユーザー作成API（設定画面用）"""
    from .serializers import UserCreateSerializer
    
    serializer = UserCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        profile_serializer = UserProfileSerializer(user)
        
        return Response(profile_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def users_list_view(request):
    """ユーザー一覧取得API（設定画面用）"""
    users = User.objects.all()
    serializer = UserProfileSerializer(users, many=True)
    
    return Response({
        'count': users.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_user_view(request, user_id):
    """ユーザー情報更新API（設定画面用）"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'ユーザーが見つかりません'}, status=status.HTTP_404_NOT_FOUND)
    
    # 部分更新のためのデータ取得
    data = request.data
    
    # 許可されるフィールドのみ更新
    allowed_fields = ['name', 'email', 'role', 'is_active']
    for field in allowed_fields:
        if field in data:
            setattr(user, field, data[field])
    
    try:
        user.save()
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


login_view.throttle_scope = 'auth_login'
mfa_resend_view.throttle_scope = 'auth_mfa_resend'
mfa_verify_view.throttle_scope = 'auth_mfa_verify'
refresh_view.throttle_scope = 'auth_refresh'
if hasattr(login_view, 'cls'):
    login_view.cls.throttle_scope = 'auth_login'
if hasattr(mfa_resend_view, 'cls'):
    mfa_resend_view.cls.throttle_scope = 'auth_mfa_resend'
if hasattr(mfa_verify_view, 'cls'):
    mfa_verify_view.cls.throttle_scope = 'auth_mfa_verify'
if hasattr(refresh_view, 'cls'):
    refresh_view.cls.throttle_scope = 'auth_refresh'
