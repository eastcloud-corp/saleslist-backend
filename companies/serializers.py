from rest_framework import serializers
from .models import Company, Executive


class ExecutiveSerializer(serializers.ModelSerializer):
    """役員情報用シリアライザー"""
    
    class Meta:
        model = Executive
        fields = [
            'id', 'name', 'position', 'facebook_url', 'other_sns_url',
            'direct_email', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompanyListSerializer(serializers.ModelSerializer):
    """企業一覧用シリアライザー"""
    ng_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'corporate_number', 'industry',
            'contact_person_name', 'contact_person_position', 'facebook_url',
            'tob_toc_type', 'business_description',
            'prefecture', 'city', 'employee_count', 'revenue', 'capital',
            'established_year', 'website_url', 'contact_email', 'phone',
            'is_global_ng', 'created_at', 'updated_at', 'ng_status'
        ]
    
    def get_ng_status(self, obj):
        """NG状態情報を取得（OpenAPI仕様準拠）"""
        # OpenAPI仕様: type は文字列 (enum: [global, client, project])
        ng_type = None
        reason = None
        
        if obj.is_global_ng:
            ng_type = 'global'
            reason = 'グローバルNG設定'
        
        # TODO: クライアントNG・プロジェクトNG判定は将来実装
        
        return {
            'is_ng': obj.is_global_ng,
            'type': ng_type,  # OpenAPI仕様: 文字列
            'reason': reason
        }


class CompanyDetailSerializer(serializers.ModelSerializer):
    """企業詳細用シリアライザー"""
    executives = ExecutiveSerializer(many=True, read_only=True)
    ng_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'industry', 'employee_count', 'revenue',
            'prefecture', 'city', 'established_year', 'website_url',
            'contact_email', 'phone', 'notes', 'is_global_ng',
            'created_at', 'updated_at', 'executives', 'ng_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_ng_status(self, obj):
        """NG状態情報を取得（OpenAPI仕様準拠）"""
        # OpenAPI仕様: type は文字列 (enum: [global, client, project])
        ng_type = None
        reason = None
        
        if obj.is_global_ng:
            ng_type = 'global'
            reason = 'グローバルNG設定'
        
        # TODO: クライアントNG・プロジェクトNG判定は将来実装
        
        return {
            'is_ng': obj.is_global_ng,
            'type': ng_type,  # OpenAPI仕様: 文字列
            'reason': reason
        }


class CompanyCreateSerializer(serializers.ModelSerializer):
    """企業作成用シリアライザー"""
    
    class Meta:
        model = Company
        fields = [
            'name', 'corporate_number', 'industry',
            'contact_person_name', 'contact_person_position', 'facebook_url',
            'tob_toc_type', 'business_description',
            'prefecture', 'city', 'employee_count', 'revenue', 'capital',
            'established_year', 'website_url', 'contact_email', 'phone', 'notes'
        ]