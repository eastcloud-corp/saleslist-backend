import logging

from celery.exceptions import CeleryError, TimeoutError
from django.conf import settings
from django.core.management.base import CommandError
from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters import rest_framework as filters
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import APIException
from django.utils import timezone
from .models import (
    Company,
    Executive,
    CompanyUpdateCandidate,
    CompanyReviewBatch,
    CompanyReviewItem,
    CompanyUpdateHistory,
)
from .importers import import_companies_csv
from projects.models import Project, ProjectCompany
from .services.review_ingestion import generate_sample_candidates, ingest_corporate_number_candidates
from .services.corporate_number_client import CorporateNumberAPIError
from .serializers import (
    CompanyListSerializer, CompanyDetailSerializer, 
    CompanyCreateSerializer, ExecutiveSerializer,
    CompanyReviewBatchListSerializer,
    CompanyReviewBatchDetailSerializer,
    CompanyReviewDecisionSerializer,
    CompanyReviewItemSerializer,
    CorporateNumberImportSerializer,
    CorporateNumberImportTriggerSerializer,
    OpenDataIngestionTriggerSerializer,
    AIIngestionTriggerSerializer,
)
from companies.tasks import (
    run_ai_ingestion_stub,
    run_corporate_number_import_task,
    run_opendata_ingestion_task,
)
from ai_enrichment.normalizers import normalize_candidate_value


logger = logging.getLogger(__name__)


ROLE_CATEGORY_DEFINITIONS = {
    'leadership': {
        'label': '代表・CEO',
        'keywords': [
            '代表取締役', '代表取締役社長', '代表', '代表者', 'CEO', 'ＣＥＯ', '社長', '会長', 'President',
            'プレジデント', 'オーナー', 'Founder', '創業者'
        ],
    },
    'board': {
        'label': '取締役・ボード',
        'keywords': [
            '取締役', '取締役会', '常務取締役', '専務取締役', '副社長', '社外取締役', '監査役',
            '非常勤取締役', '取締役会長', '取締役副社長', 'Director'
        ],
    },
    'executive': {
        'label': '執行役員・本部長',
        'keywords': [
            '執行役員', '上席執行役員', '本部長', '事業部長', '支店長', 'ゼネラルマネージャー',
            'General Manager', 'ジェネラルマネージャー'
        ],
    },
    'c_suite': {
        'label': 'CxO・経営陣',
        'keywords': [
            'COO', 'ＣＯＯ', 'CFO', 'ＣＦＯ', 'CTO', 'ＣＴＯ', 'CIO', 'ＣＩＯ', 'CSO', 'ＣＳＯ',
            'CMO', 'ＣＭＯ', 'CHRO', 'ＣＨＲＯ', 'CPO', 'ＣＰＯ', 'CXO', 'ＣＸＯ'
        ],
    },
    'advisor': {
        'label': '顧問・アドバイザー',
        'keywords': [
            '顧問', 'アドバイザー', '相談役', '顧問弁護士', '顧問税理士', 'Advisor'
        ],
    },
    'other': {
        'label': 'その他',
        'keywords': [],
    },
}

# レビュー対象フィールドのマッピング
COMPANY_FIELD_MAPPING = {
    'name': 'name',
    'industry': 'industry',
    'business_description': 'business_description',
    'prefecture': 'prefecture',
    'city': 'city',
    'employee_count': 'employee_count',
    'revenue': 'revenue',
    'capital': 'capital',
    'established_year': 'established_year',
    'website_url': 'website_url',
    'contact_email': 'contact_email',
    'phone': 'phone',
    'notes': 'notes',
    'corporate_number': 'corporate_number',
    'tob_toc_type': 'tob_toc_type',
}

INT_FIELDS = {'employee_count', 'revenue', 'capital', 'established_year'}
CHOICE_FIELDS = {
    'tob_toc_type': {choice[0] for choice in Company._meta.get_field('tob_toc_type').choices},
}


class CompanyFilter(filters.FilterSet):
    """企業フィルター"""
    industry = filters.CharFilter(method='filter_industry')
    employee_min = filters.NumberFilter(field_name='employee_count', lookup_expr='gte')
    employee_max = filters.NumberFilter(field_name='employee_count', lookup_expr='lte')
    revenue_min = filters.NumberFilter(field_name='revenue', lookup_expr='gte')
    revenue_max = filters.NumberFilter(field_name='revenue', lookup_expr='lte')
    established_year_min = filters.NumberFilter(field_name='established_year', lookup_expr='gte')
    established_year_max = filters.NumberFilter(field_name='established_year', lookup_expr='lte')
    has_facebook = filters.BooleanFilter(method='filter_has_facebook')
    exclude_ng = filters.BooleanFilter(method='filter_exclude_ng')
    role_category = filters.MultipleChoiceFilter(
        method='filter_role_category',
        choices=[(key, value['label']) for key, value in ROLE_CATEGORY_DEFINITIONS.items()],
    )
    
    class Meta:
        model = Company
        fields = ['industry', 'prefecture', 'is_global_ng', 'role_category']

    def _get_query_values(self, name, fallback_value=None):
        request = getattr(self, 'request', None)
        values = []
        if request is not None:
            values = [value for value in request.query_params.getlist(name) if value]
        if not values and fallback_value:
            values = [fallback_value]
        return values

    def filter_industry(self, queryset, name, value):
        values = [
            item.strip()
            for item in self._get_query_values(name, value)
            if isinstance(item, str) and item.strip()
        ]
        if not values:
            return queryset

        industry_query = Q()
        for item in values:
            industry_query |= Q(industry__icontains=item)

        return queryset.filter(industry_query)

    def filter_has_facebook(self, queryset, name, value):
        if value:
            return queryset.filter(executives__facebook_url__isnull=False).distinct()
        return queryset
    
    def filter_exclude_ng(self, queryset, name, value):
        if value:
            return queryset.filter(is_global_ng=False)
        return queryset

    def filter_role_category(self, queryset, name, value):
        values = [item.lower() for item in self._get_query_values(name)]
        if not values:
            return queryset

        combined_query = Q()
        known_keywords = [
            keyword
            for key, definition in ROLE_CATEGORY_DEFINITIONS.items()
            if key != 'other'
            for keyword in definition.get('keywords', [])
        ]

        for category in values:
            definition = ROLE_CATEGORY_DEFINITIONS.get(category)
            if not definition:
                continue

            keywords = definition.get('keywords', [])

            category_query = Q()
            for keyword in keywords:
                category_query |= Q(executives__position__icontains=keyword)
                category_query |= Q(contact_person_position__icontains=keyword)

            combined_query |= category_query

        if 'other' in values:
            other_query = (
                (Q(executives__position__isnull=False) & ~Q(executives__position__exact="")) |
                (Q(contact_person_position__isnull=False) & ~Q(contact_person_position__exact=""))
            )
            for keyword in known_keywords:
                other_query &= ~Q(executives__position__icontains=keyword)
                other_query &= ~Q(contact_person_position__icontains=keyword)
            combined_query |= other_query

        if not combined_query:
            return queryset

        return queryset.filter(combined_query).distinct()


class ConflictError(APIException):
    """409 Conflict を表す例外"""

    status_code = status.HTTP_409_CONFLICT
    default_detail = '既存データと競合しました'
    default_code = 'conflict'


class CompanyViewSet(viewsets.ModelViewSet):
    """企業ViewSet"""
    queryset = Company.objects.all()
    serializer_class = CompanyListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CompanyFilter
    search_fields = ['name', 'industry', 'prefecture']
    ordering_fields = ['name', 'created_at', 'employee_count', 'revenue']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CompanyDetailSerializer
        elif self.action == 'create':
            return CompanyCreateSerializer
        return CompanyListSerializer

    def _normalize_corporate_number(self, value):
        """法人番号の余分な空白を取り除く"""
        if value is None:
            return ''
        return value.strip()

    def _raise_if_duplicate_corporate_number(self, corporate_number, *, exclude_id=None):
        if not corporate_number:
            return

        queryset = Company.objects.filter(corporate_number=corporate_number)
        if exclude_id is not None:
            queryset = queryset.exclude(id=exclude_id)

        existing = queryset.first()
        if existing:
            raise ConflictError(detail={
                'message': f'法人番号「{corporate_number}」は既に企業「{existing.name}」(ID: {existing.id})で使用されています。',
                'duplicate_with': existing.id,
                'duplicate_name': existing.name,
            })

    def perform_create(self, serializer):
        corporate_number = self._normalize_corporate_number(
            serializer.validated_data.get('corporate_number')
        )
        serializer.validated_data['corporate_number'] = corporate_number
        self._raise_if_duplicate_corporate_number(corporate_number)
        serializer.save()

    def perform_update(self, serializer):
        if 'corporate_number' in serializer.validated_data:
            corporate_number = self._normalize_corporate_number(
                serializer.validated_data.get('corporate_number')
            )
        else:
            corporate_number = self._normalize_corporate_number(
                getattr(serializer.instance, 'corporate_number', '')
            )

        serializer.validated_data['corporate_number'] = corporate_number
        self._raise_if_duplicate_corporate_number(
            corporate_number,
            exclude_id=getattr(serializer.instance, 'id', None)
        )
        serializer.save()

    @action(detail=True, methods=['post'], url_path='toggle_ng')
    def toggle_ng(self, request, pk=None):
        """企業のグローバルNG状態切り替え（OpenAPI仕様準拠）"""
        company = self.get_object()
        reason = request.data.get('reason', '')
        
        company.is_global_ng = not company.is_global_ng
        # TODO: reasonをNG理由として保存する機能は将来実装
        company.save()
        
        return Response({
            'message': f'企業「{company.name}」のNG状態を{"設定" if company.is_global_ng else "解除"}しました',
            'is_global_ng': company.is_global_ng,
            'reason': reason if company.is_global_ng else None
        })
    
    @action(detail=True, methods=['get'])
    def executives(self, request, pk=None):
        """企業役員一覧取得（OpenAPI仕様準拠）"""
        company = self.get_object()
        executives = company.executives.all()
        
        serializer = ExecutiveSerializer(executives, many=True)
        
        return Response({
            'count': executives.count(),
            'results': serializer.data
        })
    
    @action(detail=False, methods=['post'], url_path='import_csv')
    def import_csv(self, request):
        """企業CSVインポート（OpenAPI仕様準拠）"""
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({
                'error': 'CSVファイルが必要です'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            result, error_payload = import_companies_csv(uploaded_file)
            if error_payload:
                return Response(error_payload, status=status.HTTP_400_BAD_REQUEST)

            return Response(result)
        except Exception as e:
            logger.exception('CSV import failed')
            return Response({
                'error': f'インポートに失敗しました: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='export_csv')  
    def export_csv(self, request):
        """企業CSVエクスポート（OpenAPI仕様準拠）"""
        # 簡易実装：CSVダウンロード
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="companies.csv"'
        response.write('企業名,業界,従業員数\n')
        return response

    @action(detail=False, methods=['post'], url_path='bulk-add-to-projects')
    def bulk_add_to_projects(self, request):
        """選択した企業を複数案件へ一括追加する"""
        company_ids = request.data.get('company_ids', [])
        project_ids = request.data.get('project_ids', [])

        if not company_ids or not project_ids:
            return Response({
                'error': 'company_ids と project_ids の両方を指定してください。'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            company_ids = [int(cid) for cid in set(company_ids)]
            project_ids = [int(pid) for pid in set(project_ids)]
        except (TypeError, ValueError):
            return Response({
                'error': 'company_ids と project_ids は数値の配列で指定してください。'
            }, status=status.HTTP_400_BAD_REQUEST)

        companies = Company.objects.filter(id__in=company_ids)
        company_map = {company.id: company for company in companies}
        missing_company_ids = sorted(set(company_ids) - set(company_map.keys()))

        projects = Project.objects.filter(id__in=project_ids).select_related('client').prefetch_related('ng_companies')
        project_map = {project.id: project for project in projects}
        missing_project_ids = sorted(set(project_ids) - set(project_map.keys()))

        if not project_map or not company_map:
            return Response({
                'error': '有効な企業または案件が見つかりません。',
                'missing_company_ids': missing_company_ids,
                'missing_project_ids': missing_project_ids,
            }, status=status.HTTP_400_BAD_REQUEST)

        total_added = 0
        project_results = []

        with transaction.atomic():
            for project in projects:
                client = project.client
                client_ng_ids = set(client.ng_companies.filter(
                    matched=True,
                    company_id__isnull=False
                ).values_list('company_id', flat=True))
                client_ng_names = set(client.ng_companies.filter(
                    matched=True
                ).values_list('company_name', flat=True))
                project_ng_ids = set(project.ng_companies.values_list('company_id', flat=True))

                existing_company_ids = set(ProjectCompany.objects.filter(
                    project=project,
                    company_id__in=company_map.keys()
                ).values_list('company_id', flat=True))

                project_summary = {
                    'project_id': project.id,
                    'project_name': project.name,
                    'added_company_ids': [],
                    'skipped': []
                }

                for company_id in company_ids:
                    company = company_map.get(company_id)
                    if not company:
                        continue

                    skip_reason = None

                    if company.is_global_ng:
                        skip_reason = 'グローバルNG企業のため追加できません'
                    elif company_id in client_ng_ids or company.name in client_ng_names:
                        ng_record = client.ng_companies.filter(company_id=company_id).first()
                        if not ng_record:
                            ng_record = client.ng_companies.filter(company_name=company.name).first()
                        detail = f"（理由: {ng_record.reason}）" if ng_record and ng_record.reason else ''
                        skip_reason = f'クライアントNG企業のため追加できません{detail}'
                    elif company_id in project_ng_ids:
                        ng_record = project.ng_companies.filter(company_id=company_id).first()
                        detail = f"（理由: {ng_record.reason}）" if ng_record and ng_record.reason else ''
                        skip_reason = f'案件NG企業のため追加できません{detail}'
                    elif company_id in existing_company_ids or company_id in project_summary['added_company_ids']:
                        skip_reason = '既に案件に追加済みです'

                    if skip_reason:
                        project_summary['skipped'].append({
                            'company_id': company_id,
                            'company_name': company.name,
                            'reason': skip_reason
                        })
                        continue

                    ProjectCompany.objects.create(
                        project=project,
                        company=company,
                        status='未接触'
                    )
                    project_summary['added_company_ids'].append(company_id)
                    existing_company_ids.add(company_id)
                    total_added += 1

                project_results.append(project_summary)

        total_requested = len(company_map) * len(project_map)

        return Response({
            'message': f'{total_added}件の企業を案件に追加しました',
            'total_requested': total_requested,
            'total_added': total_added,
            'missing_company_ids': missing_company_ids,
            'missing_project_ids': missing_project_ids,
            'projects': project_results,
        })


class CompanyReviewViewSet(viewsets.ReadOnlyModelViewSet):
    """企業補完候補レビュー用ViewSet"""

    queryset = CompanyReviewBatch.objects.all()
    serializer_class = CompanyReviewBatchListSerializer
    email_field = drf_serializers.EmailField()
    url_field = drf_serializers.URLField()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CompanyReviewBatchDetailSerializer
        if self.action == 'decide':
            return CompanyReviewDecisionSerializer
        return CompanyReviewBatchListSerializer

    def get_queryset(self):
        queryset = super().get_queryset().select_related('company', 'assigned_to').prefetch_related(
            'items__candidate'
        )
        request = getattr(self, 'request', None)
        if request is None:
            return queryset
        action = getattr(self, 'action', None)
        status_param = request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        elif action not in {'retrieve', 'decide'}:
            queryset = queryset.filter(
                status__in=[
                    CompanyReviewBatch.STATUS_PENDING,
                    CompanyReviewBatch.STATUS_IN_REVIEW,
                ]
            )

        company_name = request.query_params.get('company_name')
        if company_name:
            queryset = queryset.filter(company__name__icontains=company_name)

        source_type = request.query_params.get('source_type')
        if source_type:
            queryset = queryset.filter(items__candidate__source_type=source_type).distinct()

        target_field = request.query_params.get('field')
        if target_field and target_field != 'all':
            queryset = queryset.filter(items__field=target_field).distinct()

        confidence_min = request.query_params.get('confidence_min')
        if confidence_min:
            try:
                confidence_min = int(confidence_min)
                queryset = queryset.filter(items__confidence__gte=confidence_min).distinct()
            except ValueError:
                pass

        return queryset.order_by('-created_at')

    def _normalize_corporate_number(self, value):
        if value is None:
            return ''
        return ''.join(ch for ch in str(value).strip() if ch.isdigit())

    def _clean_value(self, field, raw_value):
        if raw_value is None:
            return None, ''

        if isinstance(raw_value, str):
            base_value = raw_value.strip()
        else:
            base_value = raw_value

        normalized_value = normalize_candidate_value(field, raw_value)
        if normalized_value is not None:
            value = normalized_value
        else:
            value = base_value

        if field in INT_FIELDS:
            if value == '':
                return None, ''
            try:
                int_value = int(value)
            except (TypeError, ValueError):
                raise drf_serializers.ValidationError({field: f'{field} は数値で指定してください。'})
            return int_value, str(int_value)

        if field == 'contact_email':
            if value == '':
                return '', ''
            email = self.email_field.to_internal_value(value)
            return email, email

        if field == 'website_url':
            if value == '':
                return '', ''
            url = self.url_field.to_internal_value(value)
            return url, url

        if field == 'tob_toc_type':
            if value and value not in CHOICE_FIELDS['tob_toc_type']:
                raise drf_serializers.ValidationError({
                    field: f'{field} は {", ".join(sorted(CHOICE_FIELDS["tob_toc_type"]))} のいずれかで指定してください。'
                })
            return value, value or ''

        if field == 'corporate_number':
            normalized = self._normalize_corporate_number(value)
            return normalized, normalized

        if isinstance(value, str):
            return value, value
        return value, str(value)

    def _apply_batch_status(self, batch):
        pending_exists = batch.items.filter(decision=CompanyReviewItem.DECISION_PENDING).exists()
        approved_exists = batch.items.filter(
            decision__in=[CompanyReviewItem.DECISION_APPROVED, CompanyReviewItem.DECISION_UPDATED]
        ).exists()
        rejected_exists = batch.items.filter(decision=CompanyReviewItem.DECISION_REJECTED).exists()

        if pending_exists:
            batch.status = CompanyReviewBatch.STATUS_IN_REVIEW
        else:
            if approved_exists and rejected_exists:
                batch.status = CompanyReviewBatch.STATUS_PARTIAL
            elif approved_exists:
                batch.status = CompanyReviewBatch.STATUS_APPROVED
            elif rejected_exists:
                batch.status = CompanyReviewBatch.STATUS_REJECTED
            else:
                batch.status = CompanyReviewBatch.STATUS_IN_REVIEW

    @action(detail=True, methods=['post'])
    def decide(self, request, pk=None):
        """レビュー項目の承認／否認を反映"""
        batch = self.get_object()
        if batch.status not in (
            CompanyReviewBatch.STATUS_PENDING,
            CompanyReviewBatch.STATUS_IN_REVIEW,
        ):
            return Response(
                {
                    'detail': 'このレビューは処理済みのため更新できません。',
                    'status': 'conflict',
                },
                status=status.HTTP_409_CONFLICT,
            )
        serializer = CompanyReviewDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items_payload = serializer.validated_data['items']

        now = timezone.now()
        auth_user = request.user if request.user and request.user.is_authenticated else None

        with transaction.atomic():
            batch = (
                CompanyReviewBatch.objects.select_for_update()
                .prefetch_related('items__candidate')
                .get(pk=batch.pk)
            )
            company = Company.objects.select_for_update().get(pk=batch.company_id)
            if batch.status not in (
                CompanyReviewBatch.STATUS_PENDING,
                CompanyReviewBatch.STATUS_IN_REVIEW,
            ):
                return Response(
                    {
                        'detail': 'このレビューは処理済みのため更新できません。',
                        'status': 'conflict',
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            items_map = {item.id: item for item in batch.items.all()}
            update_fields = set()
            history_records = []
            batch_modified = False

            for payload in items_payload:
                item_id = payload['id']
                decision = payload['decision']
                comment = payload.get('comment', '')
                new_value_input = payload.get('new_value')

                item = items_map.get(item_id)
                if not item:
                    raise drf_serializers.ValidationError({'id': f'id={item_id} のレビュー項目が見つかりません。'})

                candidate = item.candidate
                field = item.field

                if field not in COMPANY_FIELD_MAPPING:
                    raise drf_serializers.ValidationError({'field': f'{field} は現在更新対象外です。'})

                model_field = COMPANY_FIELD_MAPPING[field]

                # Determine new value based on decision
                item_update_fields = ['decision', 'comment', 'decided_by', 'decided_at', 'updated_at']

                if decision in ('approve', 'update'):
                    raw_value = candidate.candidate_value if decision == 'approve' else new_value_input
                    converted_value, display_value = self._clean_value(field, raw_value)
                    old_value = getattr(company, model_field, None)

                    setattr(company, model_field, converted_value)
                    update_fields.add(model_field)

                    history_records.append({
                        'field': field,
                        'old_value': '' if old_value is None else str(old_value),
                        'new_value': display_value,
                        'source_type': candidate.source_type,
                        'comment': comment or '',
                    })

                    # Update candidate and item values
                    candidate.candidate_value = display_value
                    candidate.value_hash = CompanyUpdateCandidate.make_value_hash(field, display_value)
                    candidate.status = CompanyUpdateCandidate.STATUS_MERGED
                    candidate.merged_at = now
                    candidate.block_reproposal = False
                    candidate.rejection_reason_code = CompanyUpdateCandidate.REJECTION_REASON_NONE
                    candidate.rejection_reason_detail = ''
                    candidate.save(update_fields=[
                        'candidate_value',
                        'value_hash',
                        'status',
                        'merged_at',
                        'block_reproposal',
                        'rejection_reason_code',
                        'rejection_reason_detail',
                        'updated_at',
                    ])

                    item.candidate_value = display_value
                    item_update_fields.append('candidate_value')
                    item.decision = (
                        CompanyReviewItem.DECISION_APPROVED
                        if decision == 'approve'
                        else CompanyReviewItem.DECISION_UPDATED
                    )
                elif decision == 'reject':
                    block_reproposal = bool(payload.get('block_reproposal'))
                    reason_code = payload.get('rejection_reason_code') or CompanyUpdateCandidate.REJECTION_REASON_NONE
                    if reason_code not in dict(CompanyUpdateCandidate.REJECTION_REASON_CHOICES):
                        raise drf_serializers.ValidationError({
                            'rejection_reason_code': f'指定された否認理由コード({reason_code})は利用できません。'
                        })

                    reason_detail = (payload.get('rejection_reason_detail') or '').strip()

                    candidate.status = CompanyUpdateCandidate.STATUS_REJECTED
                    candidate.rejected_at = now
                    candidate.block_reproposal = block_reproposal
                    candidate.rejection_reason_code = reason_code
                    candidate.rejection_reason_detail = reason_detail
                    candidate.ensure_value_hash()

                    update_candidate_fields = [
                        'status',
                        'rejected_at',
                        'block_reproposal',
                        'rejection_reason_code',
                        'rejection_reason_detail',
                        'updated_at',
                    ]
                    if candidate.value_hash:
                        update_candidate_fields.append('value_hash')

                    candidate.save(update_fields=update_candidate_fields)
                    item.decision = CompanyReviewItem.DECISION_REJECTED
                else:
                    raise drf_serializers.ValidationError({'decision': f'想定外の decision: {decision}'})

                item.comment = comment or ''
                item.decided_by = auth_user
                item.decided_at = now
                item.save(update_fields=item_update_fields)
                batch_modified = True

            # 保存処理
            if update_fields:
                update_fields.add('updated_at')
                company.save(update_fields=list(update_fields))

            for record in history_records:
                CompanyUpdateHistory.objects.create(
                    company=company,
                    field=record['field'],
                    old_value=record['old_value'],
                    new_value=record['new_value'],
                    source_type=record['source_type'],
                    approved_by=auth_user,
                    approved_at=now,
                    comment=record['comment'],
                )

            if auth_user and batch.assigned_to_id is None:
                batch.assigned_to = auth_user

            if batch_modified:
                self._apply_batch_status(batch)
                batch.updated_at = now
                save_fields = ['status', 'updated_at']
                if auth_user and batch.assigned_to:
                    save_fields.append('assigned_to')
                batch.save(update_fields=save_fields)

            batch.refresh_from_db()

        detail_serializer = CompanyReviewBatchDetailSerializer(batch)
        return Response(detail_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='generate-sample')
    def generate_sample(self, request):
        """開発用: サンプル候補を生成"""
        if not settings.DEBUG and not getattr(settings, 'ENABLE_REVIEW_SAMPLE_API', False):
            return Response(
                {'detail': 'この操作は開発環境専用です。'},
                status=status.HTTP_403_FORBIDDEN,
            )
        company_id = request.data.get('company_id')
        fields = request.data.get('fields')

        company = None
        if company_id:
            try:
                company = Company.objects.get(pk=company_id)
            except Company.DoesNotExist:
                return Response(
                    {'error': f'company_id={company_id} は存在しません'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            created_items = generate_sample_candidates(company=company, fields=fields)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - 開発用
            logger.exception("generate_sample failed")
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        batch = created_items[0].batch if created_items else None
        response = {
            'created_count': len(created_items),
            'batch_id': batch.id if batch else None,
            'company_id': batch.company_id if batch else None,
        }
        return Response(response, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='import-corporate-numbers')
    def import_corporate_numbers(self, request):
        serializer = CorporateNumberImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entries = serializer.validated_data['entries']
        created_items = ingest_corporate_number_candidates(entries)

        return Response(
            {
                'created_count': len(created_items),
                'batch_ids': sorted({item.batch_id for item in created_items}),
            },
            status=status.HTTP_201_CREATED,
        )


    @action(detail=False, methods=['post'], url_path='run-corporate-number-import')
    def run_corporate_number_import_action(self, request):
        if not settings.DEBUG:
            return Response(
                {'detail': 'この操作は開発環境でのみ利用可能です。'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CorporateNumberImportTriggerSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        payload = {
            "company_ids": serializer.validated_data.get('company_ids'),
            "limit": serializer.validated_data.get('limit'),
            "dry_run": serializer.validated_data.get('dry_run', False),
            "prefecture_strict": serializer.validated_data.get('prefecture_strict', False),
            "force_refresh": serializer.validated_data.get('force', False),
            "allow_missing_token": True,
        }

        try:
            async_result = run_corporate_number_import_task.apply_async(kwargs={"payload": payload})
            result = async_result.get(timeout=settings.CELERY_TASK_TIME_LIMIT)
        except TimeoutError:
            return Response(
                {'detail': '法人番号自動取得バッチがタイムアウトしました。'},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except CeleryError as exc:
            logger.exception("Failed to run corporate number import task: %s", exc)
            return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except CommandError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except CorporateNumberAPIError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        if result.get('skipped') or result.get('dry_run'):
            status_code = status.HTTP_200_OK
        else:
            status_code = status.HTTP_201_CREATED
        return Response(result, status=status_code)

    @action(detail=False, methods=['post'], url_path='run-ai-ingestion')
    def run_ai_ingestion(self, request):
        serializer = AIIngestionTriggerSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        payload = serializer.validated_data
        task = run_ai_ingestion_stub.delay(payload)
        response = {
            'task_id': getattr(task, 'id', None),
            'status': 'accepted',
            'message': 'AI ingestion stub dispatched.',
        }
        return Response(response, status=status.HTTP_202_ACCEPTED)


    @action(detail=False, methods=['post'], url_path='run-opendata-ingestion')
    def run_opendata_ingestion(self, request):
        if not settings.DEBUG:
            return Response(
                {'detail': 'この操作は開発環境でのみ利用可能です。'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OpenDataIngestionTriggerSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        payload = {
            "source_keys": serializer.validated_data.get('sources'),
            "limit": serializer.validated_data.get('limit'),
            "dry_run": serializer.validated_data.get('dry_run', False),
        }

        try:
            async_result = run_opendata_ingestion_task.apply_async(kwargs={"payload": payload})
            result = async_result.get(timeout=settings.CELERY_TASK_TIME_LIMIT)
        except TimeoutError:
            return Response(
                {'detail': 'オープンデータ取り込みがタイムアウトしました。'},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except CeleryError as exc:
            logger.exception("Failed to run open data ingestion task: %s", exc)
            return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        status_code = status.HTTP_200_OK if result.get("dry_run") else status.HTTP_201_CREATED
        return Response(result, status=status_code)


class ExecutiveViewSet(viewsets.ModelViewSet):
    """役員ViewSet"""
    queryset = Executive.objects.all()
    serializer_class = ExecutiveSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['company']
    search_fields = ['name', 'position']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
