from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from projects.models import SavedFilter
from .serializers import SavedFilterSerializer


class SavedFilterViewSet(viewsets.ModelViewSet):
    """保存フィルターViewSet（OpenAPI仕様準拠）"""
    queryset = SavedFilter.objects.all()
    serializer_class = SavedFilterSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']