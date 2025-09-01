from rest_framework import viewsets
from companies.models import Executive
from companies.serializers import ExecutiveSerializer


class ExecutiveViewSet(viewsets.ModelViewSet):
    """役員ViewSet（OpenAPI仕様準拠）"""
    queryset = Executive.objects.all()
    serializer_class = ExecutiveSerializer
    filter_backends = []
    ordering = ['-created_at']