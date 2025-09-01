from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, update_session_auth_hash
from django.utils import timezone
from .serializers import LoginSerializer, UserProfileSerializer
from .models import User


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """ログインAPI"""
    print(f"[DEBUG] Login request data: {request.data}")
    serializer = LoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # JWTトークンを生成
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # 最終ログイン時刻を更新
        user.last_login_at = timezone.now()
        user.save(update_fields=['last_login_at'])
        
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
    
    print(f"[DEBUG] Login validation errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """ログアウトAPI"""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({
            'message': 'ログアウトしました'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
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
def refresh_view(request):
    """トークン更新API（OpenAPI仕様準拠）"""
    refresh_token = request.data.get('refresh_token')
    
    if not refresh_token:
        return Response({
            'error': 'refresh_token が必要です'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        refresh = RefreshToken(refresh_token)
        access_token = refresh.access_token
        
        return Response({
            'access_token': str(access_token),
            'refresh_token': str(refresh)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
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
