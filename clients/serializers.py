from rest_framework import serializers
from .models import Client, ClientNGCompany


class ClientSerializer(serializers.ModelSerializer):
    """クライアント用シリアライザー"""
    project_count = serializers.SerializerMethodField()
    active_project_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = [
            'id', 'name', 'company_type', 'industry', 'contact_person', 'contact_person_position',
            'contact_email', 'contact_phone', 'address', 'website', 'notes',
            'facebook_url', 'employee_count', 'revenue', 'prefecture',
            'is_active', 'created_at', 'updated_at', 'project_count', 'active_project_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'project_count', 'active_project_count']
    
    def get_project_count(self, obj):
        """総案件数を取得"""
        return obj.projects.count()
    
    def get_active_project_count(self, obj):
        """アクティブ案件数を取得"""
        return obj.projects.filter(status='進行中').count()


class ClientCreateSerializer(serializers.ModelSerializer):
    """クライアント作成用シリアライザー"""
    
    class Meta:
        model = Client
        fields = [
            'id', 'name', 'company_type', 'industry', 'contact_person', 'contact_person_position',
            'contact_email', 'contact_phone', 'address', 'website', 'notes',
            'facebook_url', 'employee_count', 'revenue', 'prefecture'
        ]
        read_only_fields = ['id']


class ClientNGCompanySerializer(serializers.ModelSerializer):
    """クライアントNG企業用シリアライザー"""
    client_id = serializers.IntegerField(source='client.id', read_only=True)
    company_id = serializers.IntegerField(source='company.id', read_only=True)
    
    class Meta:
        model = ClientNGCompany
        fields = [
            'id', 'client', 'client_id', 'company_name', 'company', 'company_id', 'matched',
            'reason', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
