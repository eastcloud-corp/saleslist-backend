from rest_framework import serializers
from .models import (
    Industry, Status, Prefecture, ProjectProgressStatus, 
    MediaType, RegularMeetingStatus, ListAvailability, 
    ListImportSource, ServiceType
)


class IndustrySerializer(serializers.ModelSerializer):
    """業界マスター用シリアライザー"""
    sub_industries = serializers.SerializerMethodField()
    
    class Meta:
        model = Industry
        fields = ['id', 'name', 'display_order', 'is_active', 'parent_industry', 'is_category', 'sub_industries']
    
    def get_sub_industries(self, obj):
        """子業界（業種）を取得"""
        if obj.is_category:
            sub_industries = Industry.objects.filter(
                parent_industry=obj,
                is_active=True
            ).order_by('display_order', 'name')
            result = IndustrySerializer(sub_industries, many=True).data
            
            # 特殊カテゴリ（人材、農林水産、鉱業、官公庁、NPO、その他、未分類）の場合、
            # カテゴリレコード自体を業種としても扱う（nameがuniqueのため）
            special_categories = ['人材', '農林水産', '鉱業', '官公庁', 'NPO', 'その他', '未分類']
            if obj.name in special_categories and not sub_industries.exists():
                # カテゴリレコード自体を業種として返す
                return [{
                    'id': obj.id,
                    'name': obj.name,
                    'display_order': obj.display_order,
                    'is_active': obj.is_active,
                    'parent_industry': None,
                    'is_category': False,
                    'sub_industries': []
                }]
            
            return result
        return []


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