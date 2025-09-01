from rest_framework import serializers
from .models import Industry, Status


class IndustrySerializer(serializers.ModelSerializer):
    """業界マスター用シリアライザー"""
    
    class Meta:
        model = Industry
        fields = ['id', 'name', 'display_order', 'is_active']


class StatusSerializer(serializers.ModelSerializer):
    """ステータスマスター用シリアライザー"""
    
    class Meta:
        model = Status
        fields = [
            'id', 'name', 'category', 'display_order', 
            'color_code', 'description', 'is_active'
        ]