from rest_framework import serializers
from .models import (
    Company,
    Executive,
    CompanyReviewBatch,
    CompanyReviewItem,
    CompanyUpdateCandidate,
)


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
            'contact_person_name', 'contact_person_position', 'facebook_url', 'facebook_page_id',
            'tob_toc_type', 'business_description',
            'prefecture', 'city', 'employee_count', 'revenue', 'capital',
            'established_year', 'website_url', 'contact_email', 'phone',
            'is_global_ng', 'facebook_friend_count', 'facebook_latest_post_at',
            'facebook_data_synced_at', 'latest_activity_at', 'ai_last_enriched_at', 'ai_last_enriched_source',
            'created_at', 'updated_at', 'ng_status'
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
            'id', 'name', 'corporate_number', 'industry',
            'contact_person_name', 'contact_person_position', 'facebook_url', 'facebook_page_id',
            'tob_toc_type', 'business_description',
            'prefecture', 'city', 'employee_count', 'revenue', 'capital',
            'established_year', 'website_url', 'contact_email', 'phone', 
            'notes', 'is_global_ng', 'facebook_friend_count', 'facebook_latest_post_at',
            'facebook_data_synced_at', 'latest_activity_at', 'ai_last_enriched_at', 'ai_last_enriched_source',
            'created_at', 'updated_at', 'executives', 'ng_status'
        ]
        read_only_fields = [
            'id', 'facebook_friend_count', 'facebook_latest_post_at',
            'facebook_data_synced_at', 'latest_activity_at', 'ai_last_enriched_at', 'ai_last_enriched_source',
            'created_at', 'updated_at'
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


class CompanyCreateSerializer(serializers.ModelSerializer):
    """企業作成用シリアライザー"""
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'corporate_number', 'industry',
            'contact_person_name', 'contact_person_position', 'facebook_url', 'facebook_page_id',
            'tob_toc_type', 'business_description',
            'prefecture', 'city', 'employee_count', 'revenue', 'capital',
            'established_year', 'website_url', 'contact_email', 'phone', 'notes'
        ]
        read_only_fields = ['id']

    def validate_corporate_number(self, value):
        sanitized = ''.join(ch for ch in (value or '').strip() if ch.isdigit())
        return sanitized


class CompanyReviewItemSerializer(serializers.ModelSerializer):
    """レビュー項目表示用シリアライザー"""

    candidate_id = serializers.IntegerField(read_only=True)
    batch_id = serializers.IntegerField(read_only=True)
    source_type = serializers.CharField(source='candidate.source_type', read_only=True)
    source_detail = serializers.CharField(source='candidate.source_detail', read_only=True)
    collected_at = serializers.DateTimeField(source='candidate.collected_at', read_only=True)
    block_reproposal = serializers.BooleanField(source='candidate.block_reproposal', read_only=True)
    rejection_reason_code = serializers.CharField(source='candidate.rejection_reason_code', read_only=True)
    rejection_reason_detail = serializers.CharField(source='candidate.rejection_reason_detail', read_only=True)
    source_company_name = serializers.CharField(source='candidate.source_company_name', read_only=True)
    source_corporate_number = serializers.CharField(source='candidate.source_corporate_number', read_only=True)

    class Meta:
        model = CompanyReviewItem
        fields = [
            'id',
            'batch_id',
            'candidate_id',
            'field',
            'current_value',
            'candidate_value',
            'confidence',
            'source_type',
            'source_detail',
            'collected_at',
            'block_reproposal',
            'rejection_reason_code',
            'rejection_reason_detail',
            'source_company_name',
            'source_corporate_number',
            'decision',
            'comment',
            'decided_by',
            'decided_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'batch_id',
            'confidence',
            'source_type',
            'source_detail',
            'collected_at',
            'block_reproposal',
            'rejection_reason_code',
            'rejection_reason_detail',
            'source_company_name',
            'source_corporate_number',
            'decided_by',
            'decided_at',
            'created_at',
            'updated_at',
        ]


class CompanyReviewBatchListSerializer(serializers.ModelSerializer):
    """レビュー一覧表示用"""

    company_id = serializers.IntegerField(read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    pending_items = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    latest_collected_at = serializers.SerializerMethodField()
    sources = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    assigned_to_id = serializers.IntegerField(read_only=True)
    candidate_fields = serializers.SerializerMethodField()

    class Meta:
        model = CompanyReviewBatch
        fields = [
            'id',
            'company_id',
            'company_name',
            'status',
            'pending_items',
            'total_items',
            'latest_collected_at',
            'sources',
            'candidate_fields',
            'assigned_to_id',
            'assigned_to_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_pending_items(self, obj):
        return obj.items.filter(decision=CompanyReviewItem.DECISION_PENDING).count()

    def get_total_items(self, obj):
        return obj.items.count()

    def get_latest_collected_at(self, obj):
        candidates = [item.candidate.collected_at for item in obj.items.all() if item.candidate]
        if not candidates:
            return None
        return max(candidates)

    def get_sources(self, obj):
        return sorted(set(item.candidate.source_type for item in obj.items.all() if item.candidate))

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.get_username()
        return None

    def get_candidate_fields(self, obj):
        return sorted(set(item.field for item in obj.items.all()))


class CompanyReviewBatchDetailSerializer(CompanyReviewBatchListSerializer):
    """レビュー詳細表示用"""

    items = CompanyReviewItemSerializer(many=True, read_only=True)

    class Meta(CompanyReviewBatchListSerializer.Meta):
        fields = CompanyReviewBatchListSerializer.Meta.fields + ['items']


class CompanyReviewDecisionItemSerializer(serializers.Serializer):
    """レビューの承認・否認入力"""

    DECISION_CHOICES = ('approve', 'reject', 'update')

    id = serializers.IntegerField()
    decision = serializers.ChoiceField(choices=DECISION_CHOICES)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    new_value = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    block_reproposal = serializers.BooleanField(required=False)
    rejection_reason_code = serializers.ChoiceField(
        choices=CompanyUpdateCandidate.REJECTION_REASON_CHOICES,
        required=False,
        allow_blank=True,
        default=CompanyUpdateCandidate.REJECTION_REASON_NONE,
    )
    rejection_reason_detail = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate(self, attrs):
        decision = attrs.get('decision')
        new_value = attrs.get('new_value')
        if decision == 'update' and (new_value is None or new_value == ''):
            raise serializers.ValidationError('decision=update の場合は new_value が必要です。')
        if decision != 'reject':
            attrs['block_reproposal'] = False
            attrs['rejection_reason_code'] = CompanyUpdateCandidate.REJECTION_REASON_NONE
            attrs['rejection_reason_detail'] = ''
            return attrs

        block_reproposal = bool(attrs.get('block_reproposal', False))
        attrs['block_reproposal'] = block_reproposal
        attrs['rejection_reason_detail'] = (attrs.get('rejection_reason_detail') or '').strip()
        if block_reproposal and not attrs.get('rejection_reason_code'):
            attrs['rejection_reason_code'] = CompanyUpdateCandidate.REJECTION_REASON_MISMATCH
        return attrs


class CompanyReviewDecisionSerializer(serializers.Serializer):
    """レビュー決裁入力"""

    items = CompanyReviewDecisionItemSerializer(many=True, allow_empty=False)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('items は1件以上指定してください。')
        return value


class CompanyReviewBulkDecisionSerializer(serializers.Serializer):
    """レビュー一括決裁入力"""

    DECISION_CHOICES = ('approve', 'reject')

    batch_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=200,
    )
    decision = serializers.ChoiceField(choices=DECISION_CHOICES)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    def validate_batch_ids(self, value):
        unique_ids = sorted(set(value))
        if len(unique_ids) != len(value):
            raise serializers.ValidationError('batch_ids に重複があります。')
        return unique_ids

class CorporateNumberEntrySerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    corporate_number = serializers.CharField(max_length=32)
    source_detail = serializers.CharField(required=False, allow_blank=True, max_length=255)
    source_company_name = serializers.CharField(required=False, allow_blank=True, max_length=255)


class CorporateNumberImportSerializer(serializers.Serializer):
    entries = CorporateNumberEntrySerializer(many=True, allow_empty=False)

    def validate_entries(self, value):
        if not value:
            raise serializers.ValidationError('entries は1件以上指定してください。')
        return value


class CorporateNumberImportTriggerSerializer(serializers.Serializer):
    company_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=False,
    )
    limit = serializers.IntegerField(min_value=1, required=False)
    prefecture_strict = serializers.BooleanField(required=False, default=False)
    dry_run = serializers.BooleanField(required=False, default=False)
    force = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        company_ids = attrs.get('company_ids')
        limit = attrs.get('limit')

        if company_ids and limit:
            raise serializers.ValidationError('company_ids と limit は同時に指定できません。')

        if company_ids:
            attrs['company_ids'] = sorted({int(value) for value in company_ids})

        return attrs


class OpenDataIngestionTriggerSerializer(serializers.Serializer):
    sources = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        allow_empty=False,
    )
    limit = serializers.IntegerField(min_value=1, required=False)
    dry_run = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        sources = attrs.get("sources")
        limit = attrs.get("limit")

        if sources:
            normalized = [source.strip() for source in sources if isinstance(source, str) and source.strip()]
            if not normalized:
                raise serializers.ValidationError("sources に有効な値を指定してください。")
            attrs["sources"] = normalized

        if limit is not None and limit <= 0:
            raise serializers.ValidationError("limit は 1 以上で指定してください。")

        return attrs


class AIIngestionTriggerSerializer(serializers.Serializer):
    company_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=False,
    )
    fields = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        allow_empty=False,
    )
    prompt = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate(self, attrs):
        company_ids = attrs.get('company_ids')
        fields = attrs.get('fields')

        if not company_ids and not fields:
            raise serializers.ValidationError('company_ids または fields のいずれかは指定してください。')

        if company_ids:
            attrs['company_ids'] = sorted({int(value) for value in company_ids})

        if fields:
            attrs['fields'] = [field.strip() for field in fields if field and field.strip()]
            if not attrs['fields']:
                raise serializers.ValidationError('fields に有効な値を指定してください。')

        return attrs
