from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters import rest_framework as filters
from django.db import transaction
from rest_framework.exceptions import APIException
from .models import Company, Executive
from projects.models import Project, ProjectCompany
from .serializers import (
    CompanyListSerializer, CompanyDetailSerializer, 
    CompanyCreateSerializer, ExecutiveSerializer
)


class CompanyFilter(filters.FilterSet):
    """企業フィルター"""
    employee_min = filters.NumberFilter(field_name='employee_count', lookup_expr='gte')
    employee_max = filters.NumberFilter(field_name='employee_count', lookup_expr='lte')
    revenue_min = filters.NumberFilter(field_name='revenue', lookup_expr='gte')
    revenue_max = filters.NumberFilter(field_name='revenue', lookup_expr='lte')
    established_year_min = filters.NumberFilter(field_name='established_year', lookup_expr='gte')
    established_year_max = filters.NumberFilter(field_name='established_year', lookup_expr='lte')
    has_facebook = filters.BooleanFilter(method='filter_has_facebook')
    exclude_ng = filters.BooleanFilter(method='filter_exclude_ng')
    
    class Meta:
        model = Company
        fields = ['industry', 'prefecture', 'is_global_ng']
    
    def filter_has_facebook(self, queryset, name, value):
        if value:
            return queryset.filter(executives__facebook_url__isnull=False).distinct()
        return queryset
    
    def filter_exclude_ng(self, queryset, name, value):
        if value:
            return queryset.filter(is_global_ng=False)
        return queryset


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
        try:
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return Response({
                    'error': 'CSVファイルが必要です'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            import csv, io, re

            def normalize_header(header: str) -> str:
                if not header:
                    return ''

                direct_map = {
                    '名前': 'name',
                    '会社名': 'name',
                    '企業名': 'name',
                    '業種': 'industry',
                    '従業員数': 'employee_count',
                    '従業員数(あれば)': 'employee_count',
                    '売上規模': 'revenue',
                    '売上規模(あれば)': 'revenue',
                    '所在地(都道府県)': 'prefecture',
                    '所在地': 'location',
                    '会社HP': 'website_url',
                    'メールアドレス': 'contact_email',
                    '電話番号': 'phone',
                    '事業内容': 'business_description',
                    '法人番号': 'corporate_number',
                }

                header_stripped = header.strip()
                if header_stripped in direct_map:
                    return direct_map[header_stripped]

                normalized = re.sub(r"[^a-z0-9]", "_", header_stripped.lower())
                header_map = {
                    'company_name': 'name',
                    'company': 'name',
                    'name': 'name',
                    'industry': 'industry',
                    'employee_count': 'employee_count',
                    'employees': 'employee_count',
                    'revenue': 'revenue',
                    'prefecture': 'prefecture',
                    'city': 'city',
                    'location': 'location',
                    'website_url': 'website_url',
                    'website': 'website_url',
                    'contact_email': 'contact_email',
                    'email': 'contact_email',
                    'phone': 'phone',
                    'telephone': 'phone',
                    'business_description': 'business_description',
                    'description': 'business_description',
                    'corporate_number': 'corporate_number',
                }
                return header_map.get(normalized, normalized)

            def parse_int(value: str, field_key: str, field_label: str) -> int:
                if value is None:
                    return 0
                cleaned = value.strip()
                if cleaned in {'', '-', 'ー', '—'}:
                    return 0
                cleaned = cleaned.replace(',', '')
                if not re.fullmatch(r"-?\d+", cleaned):
                    raise ValueError(field_key, cleaned, f"{field_label}は数値で入力してください")
                return int(cleaned)

            csv_data = uploaded_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_data))

            if not csv_reader.fieldnames:
                return Response({
                    'error': 'CSVのヘッダーが確認できません'
                }, status=status.HTTP_400_BAD_REQUEST)

            header_map = {header: normalize_header(header) for header in csv_reader.fieldnames}

            if 'name' not in header_map.values():
                return Response({
                    'error': '企業名に対応するヘッダーが見つかりません。"name" または "会社名" 列を追加してください。'
                }, status=status.HTTP_400_BAD_REQUEST)

            errors = []
            rows_to_create = []

            for index, row in enumerate(csv_reader, start=2):
                normalized_row = {}
                for original_header, value in row.items():
                    normalized_key = header_map.get(original_header, original_header)
                    if normalized_key:
                        normalized_row[normalized_key] = (value or '').strip()

                raw_name = normalized_row.get('name', '')
                name = raw_name.strip() if raw_name else ''
                if not name:
                    name = f"インポート企業（行{index}）"

                raw_corporate_number = normalized_row.get('corporate_number', '').strip()
                corporate_number = re.sub(r'[^0-9]', '', raw_corporate_number)

                try:
                    employee_count = parse_int(normalized_row.get('employee_count', ''), 'employee_count', '従業員数')
                    revenue = parse_int(normalized_row.get('revenue', ''), 'revenue', '売上規模')
                except ValueError as exc:
                    field_key, value, message = exc.args
                    errors.append({
                        'row': index,
                        'field': field_key,
                        'value': value,
                        'message': message,
                    })
                    continue

                rows_to_create.append({
                    'row_number': index,
                    'data': {
                        'name': name,
                        'corporate_number': corporate_number,
                        'industry': normalized_row.get('industry', ''),
                        'employee_count': employee_count,
                        'revenue': revenue,
                        'prefecture': normalized_row.get('prefecture', ''),
                        'city': normalized_row.get('city', ''),
                        'website_url': normalized_row.get('website_url', ''),
                        'contact_email': normalized_row.get('contact_email', ''),
                        'phone': normalized_row.get('phone', ''),
                        'business_description': normalized_row.get('business_description', ''),
                    }
                })

            if errors:
                return Response({
                    'error': 'CSV内容にエラーが見つかりました。該当行を修正してください。',
                    'errors': errors,
                }, status=status.HTTP_400_BAD_REQUEST)

            imported_count = 0
            duplicate_entries = []
            missing_corporate_number_count = 0

            corporate_numbers_in_csv = {
                entry['data']['corporate_number']
                for entry in rows_to_create
                if entry['data']['corporate_number']
            }

            existing_companies = Company.objects.filter(
                corporate_number__in=corporate_numbers_in_csv
            )
            existing_map = {
                company.corporate_number: company for company in existing_companies
            }

            seen_corporate_numbers = set()

            for entry in rows_to_create:
                company_data = entry['data']
                corporate_number = company_data.get('corporate_number', '')

                if corporate_number:
                    if corporate_number in seen_corporate_numbers:
                        duplicate_entries.append({
                            'row': entry['row_number'],
                            'type': 'csv_duplicate',
                            'corporate_number': corporate_number,
                            'name': company_data['name'],
                            'reason': '同じCSV内で同一の法人番号が複数回指定されています。'
                        })
                        continue

                    existing = existing_map.get(corporate_number)
                    if existing:
                        duplicate_entries.append({
                            'row': entry['row_number'],
                            'type': 'existing',
                            'corporate_number': corporate_number,
                            'name': company_data['name'],
                            'existing_company_id': existing.id,
                            'existing_company_name': existing.name,
                            'reason': f'既存企業「{existing.name}」(ID: {existing.id})と法人番号が重複しています。'
                        })
                        continue

                    seen_corporate_numbers.add(corporate_number)
                else:
                    missing_corporate_number_count += 1

                Company.objects.create(**company_data)
                imported_count += 1

            return Response({
                'message': f'{imported_count}件の企業を登録しました',
                'imported_count': imported_count,
                'total_rows': len(rows_to_create),
                'duplicate_count': len(duplicate_entries),
                'duplicates': duplicate_entries,
                'missing_corporate_number_count': missing_corporate_number_count,
            })
            
        except Exception as e:
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


class ExecutiveViewSet(viewsets.ModelViewSet):
    """役員ViewSet"""
    queryset = Executive.objects.all()
    serializer_class = ExecutiveSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['company']
    search_fields = ['name', 'position']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
