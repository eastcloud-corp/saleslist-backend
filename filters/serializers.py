from rest_framework import serializers
from projects.models import SavedFilter


class SavedFilterSerializer(serializers.ModelSerializer):
    """保存フィルターシリアライザー（OpenAPI仕様準拠）"""
    
    class Meta:
        model = SavedFilter
        fields = ['id', 'name', 'filter_conditions', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']