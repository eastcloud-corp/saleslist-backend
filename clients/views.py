import csv
from typing import Dict, Iterable, List

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Client, ClientNGCompany
from .serializers import ClientSerializer, ClientCreateSerializer, ClientNGCompanySerializer


class ClientViewSet(viewsets.ModelViewSet):
    """クライアントViewSet"""
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'contact_person']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        industry = self.request.query_params.get('industry')
        
        # OpenAPI仕様: industry=all は全件取得
        if industry and industry != 'all':
            queryset = queryset.filter(industry=industry)
            
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ClientCreateSerializer
        return ClientSerializer
    
    @action(detail=True, methods=['get'], url_path='ng-companies')
    def ng_companies(self, request, pk=None):
        """クライアントNGリスト取得"""
        client = self.get_object()
        ng_companies = ClientNGCompany.objects.filter(client=client)
        
        serializer = ClientNGCompanySerializer(ng_companies, many=True)
        
        count = ng_companies.count()
        matched_count = ng_companies.filter(matched=True).count()
        unmatched_count = count - matched_count
        
        return Response({
            'count': count,
            'matched_count': matched_count,
            'unmatched_count': unmatched_count,
            'results': serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='ng-companies/add')
    def add_ng_company(self, request, pk=None):
        """NGリストに企業を追加"""
        client = self.get_object()
        company_id = request.data.get('company_id')
        company_name = request.data.get('company_name')
        reason = (request.data.get('reason') or '').strip()
        
        from companies.models import Company
        
        company = None
        matched = False

        if company_id:
            try:
                company = Company.objects.get(id=company_id)
                matched = True
                if not company_name:
                    company_name = company.name
            except Company.DoesNotExist:
                return Response({
                    'error': '指定された企業が見つかりません'
                }, status=status.HTTP_404_NOT_FOUND)

        if not company_name:
            return Response({
                'error': '企業名は必須です'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            ng_company, _ = ClientNGCompany.objects.update_or_create(
                client=client,
                company_name=company_name,
                defaults={
                    'company': company,
                    'matched': matched,
                    'reason': reason,
                    'is_active': True,
                }
            )
        
        serializer = ClientNGCompanySerializer(ng_company)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='ng-companies/bulk-add')
    def bulk_add_ng_companies(self, request, pk=None):
        """NGリストに複数企業を一括追加"""
        client = self.get_object()
        company_ids = request.data.get('company_ids', [])
        reason = (request.data.get('reason') or '').strip()
        
        if not company_ids or not isinstance(company_ids, list):
            return Response({
                'error': 'company_idsは配列形式で必須です'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(company_ids) == 0:
            return Response({
                'error': 'company_idsに少なくとも1つの企業IDが必要です'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from companies.models import Company
        
        results = {
            'added_count': 0,
            'skipped_count': 0,
            'error_count': 0,
            'added': [],
            'skipped': [],
            'errors': []
        }
        
        with transaction.atomic():
            for company_id in company_ids:
                try:
                    company = Company.objects.get(id=company_id)
                    company_name = company.name
                    matched = True
                except Company.DoesNotExist:
                    results['error_count'] += 1
                    results['errors'].append({
                        'company_id': company_id,
                        'error': f'企業ID {company_id} が見つかりません'
                    })
                    continue
                
                # 既存のNGリストに登録されているかチェック
                existing_ng = ClientNGCompany.objects.filter(
                    client=client,
                    company_name=company_name
                ).first()
                
                if existing_ng:
                    results['skipped_count'] += 1
                    results['skipped'].append({
                        'company_id': company_id,
                        'company_name': company_name,
                        'reason': '既にNGリストに登録されています'
                    })
                    continue
                
                # NGリストに追加
                ng_company, created = ClientNGCompany.objects.update_or_create(
                    client=client,
                    company_name=company_name,
                    defaults={
                        'company': company,
                        'matched': matched,
                        'reason': reason,
                        'is_active': True,
                    }
                )
                
                if created:
                    results['added_count'] += 1
                    results['added'].append({
                        'company_id': company_id,
                        'company_name': company_name,
                        'ng_id': ng_company.id
                    })
                else:
                    results['skipped_count'] += 1
                    results['skipped'].append({
                        'company_id': company_id,
                        'company_name': company_name,
                        'reason': '既にNGリストに登録されています'
                    })
        
        return Response({
            'message': f'{results["added_count"]}社をNGリストに追加しました' + 
                      (f'（{results["skipped_count"]}社スキップ、{results["error_count"]}件エラー）' 
                       if results['skipped_count'] > 0 or results['error_count'] > 0 else ''),
            'added_count': results['added_count'],
            'skipped_count': results['skipped_count'],
            'error_count': results['error_count'],
            'added': results['added'],
            'skipped': results['skipped'],
            'errors': results['errors']
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """クライアント統計情報取得"""
        client = self.get_object()
        
        stats = {
            'project_count': client.projects.count(),
            'active_project_count': client.projects.filter(status='進行中').count(),
            'completed_project_count': client.projects.filter(status='完了').count(),
            'total_companies': sum(project.project_companies.count() for project in client.projects.all()),
            'total_contacted': sum(
                project.project_companies.exclude(status='未接触').count() 
                for project in client.projects.all()
            ),
        }
        
        # 成功率計算
        total_contacted = stats['total_contacted']
        if total_contacted > 0:
            success_count = sum(
                project.project_companies.filter(status__in=['成約', 'アポ獲得']).count()
                for project in client.projects.all()
            )
            stats['success_rate'] = round((success_count / total_contacted) * 100, 1)
        else:
            stats['success_rate'] = 0.0
        
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def projects(self, request, pk=None):
        """クライアント案件一覧取得（OpenAPI仕様準拠）"""
        client = self.get_object()
        projects = client.projects.all()
        
        from projects.serializers import ProjectListSerializer
        serializer = ProjectListSerializer(projects, many=True)
        
        return Response({
            'count': projects.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['get'], url_path='available-companies')
    def available_companies(self, request, pk=None):
        """クライアント用利用可能企業一覧（NG情報付き）"""
        client = get_object_or_404(Client, pk=pk)
        from companies.models import Company

        queryset = Company.objects.all()

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(industry__icontains=search) |
                Q(prefecture__icontains=search)
            )

        industry = request.query_params.get('industry')
        if industry and industry != 'all':
            queryset = queryset.filter(industry=industry)

        prefecture = request.query_params.get('prefecture')
        if prefecture:
            queryset = queryset.filter(prefecture=prefecture)

        exclude_ng = str(request.query_params.get('exclude_ng', '')).lower() in ['1', 'true', 'yes', 'on']

        ordering_param = request.query_params.get('ordering')
        allowed_ordering = {
            'name': 'name',
            '-name': '-name',
        }
        ordering = allowed_ordering.get(ordering_param, 'name')

        if exclude_ng:
            client_ng_qs = client.ng_companies.all()
            client_ng_ids = list(
                client_ng_qs.filter(company_id__isnull=False).values_list('company_id', flat=True)
            )
            if client_ng_ids:
                queryset = queryset.exclude(id__in=client_ng_ids)
            client_ng_names = list(client_ng_qs.values_list('company_name', flat=True))
            if client_ng_names:
                queryset = queryset.exclude(name__in=client_ng_names)
            queryset = queryset.filter(is_global_ng=False)

        queryset = queryset.order_by(ordering)

        page = self.paginate_queryset(queryset)
        if page is not None:
            companies = list(page)
            data = self._serialize_companies_with_ng(companies, client)
            return self.get_paginated_response(data)

        companies = list(queryset)
        data = self._serialize_companies_with_ng(companies, client)
        return Response({
            'count': len(companies),
            'results': data
        })

    @action(detail=True, methods=['get'], url_path='export-companies')
    def export_companies(self, request, pk=None):
        """クライアント配下の案件企業をCSVエクスポート"""
        client = self.get_object()

        from projects.models import ProjectCompany

        project_companies = (
            ProjectCompany.objects.filter(project__client=client)
            .select_related('project', 'company')
            .order_by('project__id', 'company__name')
        )

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename=\"client_{client.id}_companies.csv\"'

        # BOMを追加してExcelで正しく日本語を表示
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow([
            'client_name',
            'project_id',
            'project_name',
            'company_id',
            'company_name',
            'industry',
            'status',
            'contact_date',
            'staff_name',
            'is_active',
            'notes',
            'created_at',
            'updated_at',
        ])

        for pc in project_companies:
            company = pc.company
            project = pc.project
            writer.writerow([
                client.name,
                project.id,
                project.name,
                company.id,
                company.name,
                company.industry,
                pc.status,
                pc.contact_date.isoformat() if pc.contact_date else '',
                pc.staff_name or '',
                '1' if pc.is_active else '0',
                pc.notes or '',
                pc.created_at.isoformat() if pc.created_at else '',
                pc.updated_at.isoformat() if pc.updated_at else '',
            ])

        return response
    
    @action(detail=True, methods=['post'], url_path='ng-companies/import')
    def import_ng_companies(self, request, pk=None):
        """NGリストCSVインポート（OpenAPI仕様準拠）"""
        client = self.get_object()
        
        try:
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return Response({
                    'error': 'CSVファイルが必要です'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # CSV読み込み・処理
            import csv, io
            csv_data = uploaded_file.read().decode('utf-8-sig')
            csv_reader = csv.DictReader(io.StringIO(csv_data))

            if not csv_reader.fieldnames:
                return Response({
                    'error': 'CSVのヘッダーが確認できません'
                }, status=status.HTTP_400_BAD_REQUEST)

            imported_count = 0
            matched_count = 0
            unmatched_count = 0
            errors: List[str] = []

            from companies.models import Company

            for index, row in enumerate(csv_reader, start=2):  # ヘッダーを1行目と想定
                company_name = self._extract_csv_value(row, ['company_name', '企業名'])
                reason = self._extract_csv_value(row, ['reason', '理由'])

                if not company_name:
                    errors.append(f'{index}行目: 企業名が入力されていません')
                    continue

                existing_ng = ClientNGCompany.objects.filter(
                    client=client,
                    company_name=company_name
                ).first()

                company_obj = Company.objects.filter(name__iexact=company_name).first()
                matched = company_obj is not None

                if not matched and existing_ng and existing_ng.company:
                    company_obj = existing_ng.company
                    matched = existing_ng.matched

                ng_company, _ = ClientNGCompany.objects.update_or_create(
                    client=client,
                    company_name=company_name,
                    defaults={
                        'company': company_obj,
                        'matched': matched,
                        'reason': reason,
                        'is_active': True,
                    }
                )

                imported_count += 1
                if matched:
                    matched_count += 1
                else:
                    unmatched_count += 1

            return Response({
                'message': f'{imported_count}件のNG企業を登録しました',
                'imported_count': imported_count,
                'matched_count': matched_count,
                'unmatched_count': unmatched_count,
                'errors': errors,
            })
            
        except Exception as e:
            return Response({
                'error': f'インポートに失敗しました: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['delete'], url_path='ng-companies/(?P<ng_id>[0-9]+)')
    def delete_ng_company(self, request, pk=None, ng_id=None):
        """クライアントNG企業削除（OpenAPI仕様準拠）"""
        client = self.get_object()
        try:
            ng_company = ClientNGCompany.objects.get(
                client=client, 
                id=ng_id
            )
            ng_company.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ClientNGCompany.DoesNotExist:
            return Response({
                'error': 'NG企業が見つかりません'
            }, status=status.HTTP_404_NOT_FOUND)

    def _serialize_companies_with_ng(self, companies: List, client: Client) -> List[Dict]:
        """企業リストにNG情報を添付して返す"""
        from companies.serializers import CompanyListSerializer

        companies_list = list(companies)
        serializer = CompanyListSerializer(companies_list, many=True)
        data = list(serializer.data)

        client_ng_records = list(client.ng_companies.all())
        client_ng_by_id = {
            ng.company_id: ng for ng in client_ng_records if ng.company_id
        }
        client_ng_by_name = {
            ng.company_name: ng for ng in client_ng_records
        }

        for item, company in zip(data, companies_list):
            reasons: Dict[str, object] = {}
            types: List[str] = []
            is_ng = False

            if getattr(company, 'is_global_ng', False):
                is_ng = True
                types.append('global')
                reasons['global'] = 'グローバルNG設定'

            ng_record = client_ng_by_id.get(company.id) or client_ng_by_name.get(company.name)
            if ng_record:
                is_ng = True
                if 'client' not in types:
                    types.append('client')
                reasons['client'] = {
                    'id': client.id,
                    'client_id': client.id,
                    'name': client.name,
                    'reason': ng_record.reason or ''
                }

            item['ng_status'] = {
                'is_ng': is_ng,
                'types': types,
                'type': types[0] if types else None,
                'reasons': reasons
            }

        return data

    @staticmethod
    def _extract_csv_value(row: Dict[str, str], candidates: Iterable[str]) -> str:
        for key in candidates:
            if key in row and row[key] is not None:
                return row[key].strip()
        return ''


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_ng_company_direct(request, client_id, ng_id):
    """クライアントNG企業削除（直接エンドポイント）"""
    try:
        client = Client.objects.get(id=client_id)
        ng_company = ClientNGCompany.objects.get(
            client=client, 
            id=ng_id
        )
        ng_company.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except (Client.DoesNotExist, ClientNGCompany.DoesNotExist):
        return Response({
            'error': 'リソースが見つかりません'
        }, status=status.HTTP_404_NOT_FOUND)
