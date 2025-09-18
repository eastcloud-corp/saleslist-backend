from rest_framework import serializers
from .models import Project, ProjectCompany, ProjectNGCompany, ProjectEditLock
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
            'id', 'name', 'client_id', 'description', 'manager', 'assigned_user',
            'target_industry', 'target_company_size', 'dm_template',
            'start_date', 'end_date'
        ]
        read_only_fields = ['id']
    
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


class ProjectManagementListSerializer(serializers.ModelSerializer):
    """案件管理一覧用シリアライザー（新機能対応）"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    service_type = serializers.CharField(source='service_type.name', read_only=True)
    media_type = serializers.CharField(source='media_type.name', read_only=True)
    progress_status = serializers.CharField(source='progress_status.name', read_only=True)
    regular_meeting_status = serializers.CharField(source='regular_meeting_status.name', read_only=True)
    list_availability = serializers.CharField(source='list_availability.name', read_only=True)
    list_import_source = serializers.CharField(source='list_import_source.name', read_only=True)
    company_count = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()
    locked_by = serializers.SerializerMethodField()
    locked_by_name = serializers.SerializerMethodField()
    locked_until = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'client_name', 'service_type', 'media_type',
            'director', 'operator', 'sales_person',
            'operation_start_date', 'expected_end_date',
            'regular_meeting_status', 'regular_meeting_date', 'list_availability', 'list_import_source',
            'progress_status', 'entry_date_sales',
            'progress_tasks', 'daily_tasks', 'reply_check_notes', 'remarks', 'complaints_requests',
            'director_login_available', 'operator_group_invited',
            'appointment_count', 'approval_count', 'reply_count', 'friends_count',
            'situation', 'company_count', 'is_locked', 'locked_by', 'locked_by_name', 'locked_until',
            'created_at', 'updated_at'
        ]
    
    def get_is_locked(self, obj):
        """ロック状態を取得"""
        try:
            lock = obj.edit_lock
            return not lock.is_expired()
        except:
            return False
    
    def get_locked_by(self, obj):
        """ロック中ユーザーIDを取得"""
        try:
            lock = obj.edit_lock
            return lock.user.id if not lock.is_expired() else None
        except:
            return None
    
    def get_locked_by_name(self, obj):
        """ロック中ユーザー名を取得"""
        try:
            lock = obj.edit_lock
            return lock.user.name if not lock.is_expired() else None
        except:
            return None
    
    def get_locked_until(self, obj):
        """ロック期限を取得"""
        try:
            lock = obj.edit_lock
            return lock.expires_at.isoformat() if not lock.is_expired() else None
        except:
            return None
    
    def get_company_count(self, obj):
        """追加企業数を取得"""
        return obj.project_companies.count()


class ProjectManagementDetailSerializer(serializers.ModelSerializer):
    """案件管理詳細用シリアライザー（新機能対応・全項目）"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    service_type = serializers.CharField(source='service_type.name', read_only=True)
    media_type = serializers.CharField(source='media_type.name', read_only=True)
    progress_status = serializers.CharField(source='progress_status.name', read_only=True)
    regular_meeting_status = serializers.CharField(source='regular_meeting_status.name', read_only=True)
    list_availability = serializers.CharField(source='list_availability.name', read_only=True)
    list_import_source = serializers.CharField(source='list_import_source.name', read_only=True)
    
    # IDフィールドも含める
    progress_status_id = serializers.IntegerField(source='progress_status.id', read_only=True)
    service_type_id = serializers.IntegerField(source='service_type.id', read_only=True)
    media_type_id = serializers.IntegerField(source='media_type.id', read_only=True)
    regular_meeting_status_id = serializers.IntegerField(source='regular_meeting_status.id', read_only=True)
    list_availability_id = serializers.IntegerField(source='list_availability.id', read_only=True)
    list_import_source_id = serializers.IntegerField(source='list_import_source.id', read_only=True)
    company_count = serializers.SerializerMethodField()
    companies = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            # 基本情報
            'id', 'name', 'client_name', 'location_prefecture', 'industry', 'service_type',
            # リンク情報
            'operation_sheet_link', 'report_link', 'account_link',
            # 媒体・制限情報
            'media_type', 'restrictions', 'contact_info',
            # 数値データ
            'appointment_count', 'approval_count', 'reply_count', 'friends_count',
            # 状況・進行管理
            'situation', 'progress_status',
            # チェック・タスク管理
            'reply_check_notes', 'daily_tasks', 'progress_tasks', 'remarks', 'complaints_requests',
            # NG・課題管理
            'client_ng_operational_barriers', 'issues_improvements',
            # 担当者情報
            'director', 'operator', 'sales_person', 'assignment_available',
            # チェックボックス項目
            'director_login_available', 'operator_group_invited',
            # 契約・期間情報
            'contract_period', 'entry_date_sales', 'operation_start_date', 'expected_end_date', 'period_extension',
            # 定例会情報
            'regular_meeting_status', 'regular_meeting_date',
            # リスト情報
            'list_availability', 'list_import_source', 'list_count', 'company_count', 'companies',
            # 外部キーIDフィールド
            'progress_status_id', 'service_type_id', 'media_type_id', 
            'regular_meeting_status_id', 'list_availability_id', 'list_import_source_id',
            # システム管理
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_company_count(self, obj):
        """追加企業数を取得"""
        return obj.project_companies.count()

    def get_companies(self, obj):
        """関連企業一覧を取得"""
        project_companies = obj.project_companies.select_related('company').all()
        return ProjectCompanySerializer(project_companies, many=True).data


class ProjectManagementUpdateSerializer(serializers.ModelSerializer):
    """案件管理更新用シリアライザー（全編集項目対応）"""
    progress_status_id = serializers.IntegerField(write_only=True, required=False)
    service_type_id = serializers.IntegerField(write_only=True, required=False)
    media_type_id = serializers.IntegerField(write_only=True, required=False)
    regular_meeting_status_id = serializers.IntegerField(write_only=True, required=False)
    list_availability_id = serializers.IntegerField(write_only=True, required=False)
    list_import_source_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Project
        fields = [
            # 数値フィールド
            'appointment_count', 'approval_count', 'reply_count', 'friends_count',
            # ブール値フィールド
            'director_login_available', 'operator_group_invited',
            # テキストフィールド
            'situation', 'progress_tasks', 'daily_tasks', 'reply_check_notes', 'remarks', 'complaints_requests',
            'director', 'operator', 'sales_person',
            # 日付フィールド
            'regular_meeting_date', 'entry_date_sales', 'operation_start_date', 'expected_end_date',
            # 外部キーID
            'progress_status_id', 'service_type_id', 'media_type_id', 
            'regular_meeting_status_id', 'list_availability_id', 'list_import_source_id'
        ]
    
    def update(self, instance, validated_data):
        # 外部キーの処理
        foreign_key_mappings = {
            'progress_status_id': ('progress_status', 'masters.models', 'ProjectProgressStatus'),
            'service_type_id': ('service_type', 'masters.models', 'ServiceType'),
            'media_type_id': ('media_type', 'masters.models', 'MediaType'),
            'regular_meeting_status_id': ('regular_meeting_status', 'masters.models', 'RegularMeetingStatus'),
            'list_availability_id': ('list_availability', 'masters.models', 'ListAvailability'),
            'list_import_source_id': ('list_import_source', 'masters.models', 'ListImportSource'),
        }
        
        for id_field, (field_name, module_path, model_name) in foreign_key_mappings.items():
            if id_field in validated_data:
                obj_id = validated_data.pop(id_field)
                if obj_id:
                    try:
                        # 直接インポートして処理
                        from masters.models import (
                            ProjectProgressStatus, ServiceType, MediaType, 
                            RegularMeetingStatus, ListAvailability, ListImportSource
                        )
                        
                        model_mapping = {
                            'ProjectProgressStatus': ProjectProgressStatus,
                            'ServiceType': ServiceType,
                            'MediaType': MediaType,
                            'RegularMeetingStatus': RegularMeetingStatus,
                            'ListAvailability': ListAvailability,
                            'ListImportSource': ListImportSource
                        }
                        
                        model_class = model_mapping[model_name]
                        obj = model_class.objects.get(id=obj_id)
                        validated_data[field_name] = obj
                    except (KeyError, model_class.DoesNotExist) as e:
                        raise serializers.ValidationError({id_field: f'無効なID: {obj_id} - {e}'})
                else:
                    validated_data[field_name] = None
        
        # 通常のフィールド更新
        return super().update(instance, validated_data)
    companies = serializers.SerializerMethodField()
