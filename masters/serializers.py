from rest_framework import serializers
from .models import (
    Industry, Status, Prefecture, ProjectProgressStatus, 
    MediaType, RegularMeetingStatus, ListAvailability, 
    ListImportSource, ServiceType
)


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


class PrefectureSerializer(serializers.ModelSerializer):
    """都道府県マスター用シリアライザー"""
    
    class Meta:
        model = Prefecture
        fields = ['id', 'name', 'region', 'display_order', 'is_active']


class ProjectProgressStatusSerializer(serializers.ModelSerializer):
    """案件進行状況マスター用シリアライザー"""
    
    class Meta:
        model = ProjectProgressStatus
        fields = ['id', 'name', 'display_order', 'color_code', 'description', 'is_active']


class MediaTypeSerializer(serializers.ModelSerializer):
    """媒体マスター用シリアライザー"""
    
    class Meta:
        model = MediaType
        fields = ['id', 'name', 'display_order', 'description', 'is_active']


class RegularMeetingStatusSerializer(serializers.ModelSerializer):
    """定例会ステータスマスター用シリアライザー"""
    
    class Meta:
        model = RegularMeetingStatus
        fields = ['id', 'name', 'display_order', 'description', 'is_active']


class ListAvailabilitySerializer(serializers.ModelSerializer):
    """リスト有無マスター用シリアライザー"""
    
    class Meta:
        model = ListAvailability
        fields = ['id', 'name', 'display_order', 'description', 'is_active']


class ListImportSourceSerializer(serializers.ModelSerializer):
    """リスト輸入先マスター用シリアライザー"""
    
    class Meta:
        model = ListImportSource
        fields = ['id', 'name', 'display_order', 'description', 'is_active']


class ServiceTypeSerializer(serializers.ModelSerializer):
    """サービスマスター用シリアライザー"""
    
    class Meta:
        model = ServiceType
        fields = ['id', 'name', 'display_order', 'description', 'is_active']