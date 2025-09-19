from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters import rest_framework as filters
from django.db import transaction
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
            
            import csv, io
            csv_data = uploaded_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_data))
            
            imported_count = 0
            for row in csv_reader:
                name = row.get('name', '').strip()
                if name:
                    Company.objects.get_or_create(
                        name=name,
                        defaults={
                            'industry': row.get('industry', ''),
                            'employee_count': int(row.get('employee_count', 0) or 0),
                            'revenue': int(row.get('revenue', 0) or 0),
                            'prefecture': row.get('prefecture', ''),
                            'city': row.get('city', ''),
                            'website_url': row.get('website_url', ''),
                            'contact_email': row.get('contact_email', ''),
                            'phone': row.get('phone', ''),
                            'business_description': row.get('business_description', ''),
                        }
                    )
                    imported_count += 1
            
            return Response({
                'message': f'{imported_count}件の企業を登録しました',
                'imported_count': imported_count
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
