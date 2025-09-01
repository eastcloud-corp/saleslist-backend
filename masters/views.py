from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Industry, Status
from .serializers import IndustrySerializer, StatusSerializer


class IndustryViewSet(viewsets.ReadOnlyModelViewSet):
    """業界マスターViewSet"""
    queryset = Industry.objects.filter(is_active=True)
    serializer_class = IndustrySerializer
    ordering = ['display_order', 'name']
    
    def list(self, request, *args, **kwargs):
        """業界一覧取得（カスタムレスポンス形式）"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data
        })


class StatusViewSet(viewsets.ReadOnlyModelViewSet):
    """ステータスマスターViewSet"""
    queryset = Status.objects.filter(is_active=True)
    serializer_class = StatusSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category']
    ordering = ['category', 'display_order', 'name']
    
    def list(self, request, *args, **kwargs):
        """ステータス一覧取得（カスタムレスポンス形式）"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def prefectures_list(request):
    """都道府県一覧取得（OpenAPI仕様準拠）"""
    # OpenAPI仕様: 文字列配列を返却
    prefectures = [
        "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
        "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
        "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
        "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
        "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
        "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
        "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
    ]
    
    return Response(prefectures)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_statuses_list(request):
    """営業ステータス一覧取得"""
    sales_statuses = Status.objects.filter(
        category='sales',
        is_active=True
    ).order_by('display_order')
    
    serializer = StatusSerializer(sales_statuses, many=True)
    return Response({
        'results': serializer.data
    })
