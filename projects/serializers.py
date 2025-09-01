from rest_framework import serializers
from .models import Project, ProjectCompany, ProjectNGCompany
from companies.serializers import CompanyListSerializer


class ProjectListSerializer(serializers.ModelSerializer):
    """案件一覧用シリアライザー"""
    client_company = serializers.CharField(source='client.name', read_only=True)
    company_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'client_company', 'description', 'manager', 
            'assigned_user', 'status', 'start_date', 'end_date',
            'created_at', 'updated_at', 'company_count'
        ]
    
    def get_company_count(self, obj):
        """関連企業数を取得"""
        return obj.project_companies.count()


class ProjectDetailSerializer(serializers.ModelSerializer):
    """案件詳細用シリアライザー"""
    client_company = serializers.CharField(source='client.name', read_only=True)
    client = serializers.PrimaryKeyRelatedField(read_only=True)
    companies = serializers.SerializerMethodField()
    company_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'client', 'client_company', 'description', 
            'manager', 'assigned_user', 'target_industry', 'target_company_size',
            'dm_template', 'status', 'start_date', 'end_date',
            'created_at', 'updated_at', 'companies', 'company_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'client']
    
    def get_companies(self, obj):
        """関連企業一覧を取得"""
        project_companies = obj.project_companies.select_related('company').all()
        return ProjectCompanySerializer(project_companies, many=True).data
    
    def get_company_count(self, obj):
        """関連企業数を取得"""
        return obj.project_companies.count()


class ProjectCreateSerializer(serializers.ModelSerializer):
    """案件作成用シリアライザー"""
    client_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Project
        fields = [
            'name', 'client_id', 'description', 'manager', 'assigned_user',
            'target_industry', 'target_company_size', 'dm_template',
            'start_date', 'end_date'
        ]
    
    def create(self, validated_data):
        client_id = validated_data.pop('client_id')
        from clients.models import Client
        client = Client.objects.get(id=client_id)
        validated_data['client'] = client
        return super().create(validated_data)


class ProjectCompanySerializer(serializers.ModelSerializer):
    """案件企業用シリアライザー"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_industry = serializers.CharField(source='company.industry', read_only=True)
    company_id = serializers.IntegerField(source='company.id', read_only=True)
    
    class Meta:
        model = ProjectCompany
        fields = [
            'id', 'project', 'company', 'company_id', 'company_name', 'company_industry',
            'status', 'contact_date', 'staff_name', 'notes', 'is_active',
            'appointment_count', 'last_appointment_date', 'appointment_result',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']