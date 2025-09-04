from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Project, ProjectCompany, ProjectNGCompany, SalesHistory
from .serializers import (
    ProjectListSerializer, ProjectDetailSerializer, 
    ProjectCreateSerializer, ProjectCompanySerializer
)
from companies.models import Company


class ProjectViewSet(viewsets.ModelViewSet):
    """案件ViewSet"""
    queryset = Project.objects.select_related('client').all()
    serializer_class = ProjectListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['client', 'status', 'manager']
    search_fields = ['name', 'description', 'client__name']
    ordering_fields = ['name', 'created_at', 'start_date']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProjectDetailSerializer
        elif self.action == 'create':
            return ProjectCreateSerializer
        return ProjectListSerializer
    
    @action(detail=True, methods=['get'])
    def companies(self, request, pk=None):
        """案件企業一覧取得"""
        project = self.get_object()
        project_companies = ProjectCompany.objects.filter(project=project).select_related('company')
        serializer = ProjectCompanySerializer(project_companies, many=True)
        
        return Response({
            'count': project_companies.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='add-companies')
    def add_companies(self, request, pk=None):
        """案件に企業を追加"""
        project = self.get_object()
        company_ids = request.data.get('company_ids', [])
        
        if not company_ids:
            return Response({
                'error': '企業IDが指定されていません'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        added_count = 0
        errors = []
        
        for company_id in company_ids:
            try:
                company = Company.objects.get(id=company_id)
                _, created = ProjectCompany.objects.get_or_create(
                    project=project,
                    company=company,
                    defaults={'status': '未接触'}
                )
                if created:
                    added_count += 1
            except Company.DoesNotExist:
                errors.append(f'企業ID {company_id} が見つかりません')
        
        return Response({
            'message': f'{added_count}社を案件に追加しました',
            'added_count': added_count,
            'errors': errors
        })
    
    @action(detail=True, methods=['get'], url_path='available-companies')
    def available_companies(self, request, pk=None):
        """案件に追加可能な企業一覧（NG企業情報付き）"""
        project = self.get_object()
        
        # 既に追加済みの企業IDを取得
        added_company_ids = ProjectCompany.objects.filter(
            project=project
        ).values_list('company_id', flat=True)
        
        # まだ追加されていない企業を取得（NG企業も含める）
        available_companies = Company.objects.exclude(
            id__in=added_company_ids
        )
        
        # クライアントのNG企業IDを取得
        client_ng_company_ids = list(project.client.ng_companies.filter(
            matched=True
        ).values_list('company_id', flat=True))
        
        # ページネーション対応
        page = self.paginate_queryset(available_companies)
        if page is not None:
            from companies.serializers import CompanyListSerializer
            companies_data = CompanyListSerializer(page, many=True).data
            
            # 各企業にNG情報を付与
            for company_data in companies_data:
                company_id = company_data['id']
                
                # NG状態の判定
                is_global_ng = company_data.get('is_global_ng', False)
                is_client_ng = company_id in client_ng_company_ids
                
                company_data['ng_status'] = {
                    'is_ng': is_global_ng or is_client_ng,
                    'types': [],
                    'reasons': {}
                }
                
                if is_global_ng:
                    company_data['ng_status']['types'].append('global')
                    company_data['ng_status']['reasons']['global'] = 'グローバルNG設定'
                
                if is_client_ng:
                    company_data['ng_status']['types'].append('client')
                    # クライアントNG理由を取得
                    ng_record = project.client.ng_companies.filter(
                        company_id=company_id, matched=True
                    ).first()
                    if ng_record:
                        company_data['ng_status']['reasons']['client'] = {
                            'id': project.client.id,
                            'name': project.client.name,
                            'reason': ng_record.reason
                        }
            
            return self.get_paginated_response(companies_data)
        
        from companies.serializers import CompanyListSerializer
        serializer = CompanyListSerializer(available_companies, many=True)
        return Response({
            'count': available_companies.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='bulk_update_status')
    def bulk_update_status(self, request, pk=None):
        """案件企業一括ステータス更新（OpenAPI仕様準拠）"""
        project = self.get_object()
        company_ids = request.data.get('company_ids', [])
        new_status = request.data.get('status', '')
        
        if not company_ids or not new_status:
            return Response({
                'error': 'company_ids と status が必要です'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        updated_count = ProjectCompany.objects.filter(
            project=project,
            company_id__in=company_ids
        ).update(status=new_status)
        
        return Response({
            'message': f'{updated_count}社のステータスを更新しました',
            'updated_count': updated_count,
            'status': new_status
        })
    
    @action(detail=False, methods=['post'], url_path='import_csv')
    def import_csv(self, request):
        """案件CSVインポート"""
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
                    Project.objects.get_or_create(
                        name=name,
                        defaults={
                            'client_company': row.get('client_company', ''),
                            'description': row.get('description', ''),
                            'manager_name': row.get('manager_name', ''),
                            'status': row.get('status', 'planning'),
                        }
                    )
                    imported_count += 1
            
            return Response({
                'message': f'{imported_count}件の案件を登録しました',
                'imported_count': imported_count
            })
            
        except Exception as e:
            return Response({
                'error': f'インポートに失敗しました: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='export_csv')
    def export_csv(self, request, pk=None):
        """案件CSVエクスポート（OpenAPI仕様準拠）"""
        project = self.get_object()
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="project_{project.id}.csv"'
        
        import csv
        writer = csv.writer(response)
        writer.writerow(['company_name', 'status', 'contact_date', 'notes'])
        
        # ProjectCompany データをエクスポート
        from .models import ProjectCompany
        for pc in ProjectCompany.objects.filter(project=project).select_related('company'):
            writer.writerow([
                pc.company.name,
                pc.status,
                pc.contact_date.strftime('%Y-%m-%d') if pc.contact_date else '',
                pc.notes,
            ])
        
        return response
    
    @action(detail=True, methods=['get'], url_path='ng_companies')
    def ng_companies(self, request, pk=None):
        """案件NG企業一覧取得（OpenAPI仕様準拠）"""
        project = self.get_object()
        ng_companies = ProjectNGCompany.objects.filter(project=project)
        
        results = []
        for ng_company in ng_companies:
            results.append({
                'id': ng_company.id,
                'company_id': ng_company.company.id,
                'company_name': ng_company.company.name,
                'reason': ng_company.reason,
                'created_at': ng_company.created_at
            })
        
        return Response({
            'count': ng_companies.count(),
            'results': results
        })


class ProjectCompanyViewSet(viewsets.ModelViewSet):
    """案件企業個別操作ViewSet（OpenAPI仕様準拠）"""
    queryset = ProjectCompany.objects.all()
    serializer_class = ProjectCompanySerializer
    
    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        if project_id:
            return ProjectCompany.objects.filter(project_id=project_id)
        return super().get_queryset()
    
    def update(self, request, *args, **kwargs):
        """案件企業ステータス更新（OpenAPI仕様準拠）"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """案件から企業を削除（OpenAPI仕様準拠）"""
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def project_company_detail(request, project_id, company_id):
    """プロジェクト企業個別操作（OpenAPI仕様準拠）"""
    try:
        project_company = ProjectCompany.objects.get(
            project_id=project_id,
            company_id=company_id
        )
        
        if request.method in ['PUT', 'PATCH']:
            # ステータス更新 + 営業履歴記録
            new_status = request.data.get('status', project_company.status)
            notes = request.data.get('notes', project_company.notes or '')
            staff_name = request.data.get('staff_name', project_company.staff_name)
            is_active = request.data.get('is_active', project_company.is_active)
            
            # ステータス変更時は履歴記録
            if new_status != project_company.status:
                from .models import SalesHistory
                from datetime import date
                
                SalesHistory.objects.create(
                    project_company=project_company,
                    status=new_status,
                    status_date=date.today(),
                    staff_name=staff_name,
                    notes=notes
                )
            
            project_company.status = new_status
            project_company.staff_name = staff_name
            project_company.is_active = is_active
            if notes:
                project_company.notes = notes
            project_company.save()
            
            serializer = ProjectCompanySerializer(project_company)
            return Response(serializer.data)
        
        elif request.method == 'DELETE':
            # 企業削除
            project_company.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
    except ProjectCompany.DoesNotExist:
        return Response({
            'error': 'プロジェクト企業関係が見つかりません'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_target_company_detail(request, project_id, company_id):
    """営業先企業詳細情報取得"""
    try:
        project_company = ProjectCompany.objects.select_related('company').get(
            project_id=project_id,
            company_id=company_id
        )
        
        return Response({
            'id': project_company.id,
            'project_id': project_company.project_id,
            'company_id': project_company.company_id,
            'company': {
                'id': project_company.company.id,
                'name': project_company.company.name,
                'industry': project_company.company.industry,
                'prefecture': project_company.company.prefecture,
                'city': project_company.company.city,
                'employee_count': project_company.company.employee_count,
                'website_url': project_company.company.website_url,
            },
            'status': project_company.status,
            'contact_date': project_company.contact_date,
            'next_action': getattr(project_company, 'next_action', ''),
            'notes': project_company.notes,
            'staff_name': project_company.staff_name,
            'added_at': project_company.created_at,
            'updated_at': project_company.updated_at,
        })
        
    except ProjectCompany.DoesNotExist:
        return Response({
            'error': '営業先企業が見つかりません'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'サーバーエラー: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def sales_history(request, project_id, company_id):
    """営業履歴管理"""
    try:
        project_company = ProjectCompany.objects.get(
            project_id=project_id,
            company_id=company_id
        )
        
        if request.method == 'GET':
            # 営業履歴一覧取得
            history = SalesHistory.objects.filter(project_company=project_company)
            
            results = []
            for h in history:
                results.append({
                    'id': h.id,
                    'status': h.status,
                    'status_date': h.status_date,
                    'staff_name': h.staff_name,
                    'notes': h.notes,
                    'created_at': h.created_at,
                })
            
            return Response({
                'count': history.count(),
                'results': results
            })
        
        elif request.method == 'POST':
            # 営業履歴追加
            status_value = request.data.get('status')
            status_date = request.data.get('status_date')
            staff_name = request.data.get('staff_name', '')
            notes = request.data.get('notes', '')
            
            if not status_value or not status_date:
                return Response({
                    'error': 'ステータスと日付は必須です'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            history = SalesHistory.objects.create(
                project_company=project_company,
                status=status_value,
                status_date=status_date,
                staff_name=staff_name,
                notes=notes
            )
            
            return Response({
                'id': history.id,
                'status': history.status,
                'status_date': history.status_date,
                'staff_name': history.staff_name,
                'notes': history.notes,
                'created_at': history.created_at,
            }, status=status.HTTP_201_CREATED)
            
    except ProjectCompany.DoesNotExist:
        return Response({
            'error': '営業先企業が見つかりません'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def sales_history_detail(request, project_id, company_id, history_id):
    """営業履歴個別操作"""
    try:
        project_company = ProjectCompany.objects.get(
            project_id=project_id,
            company_id=company_id
        )
        
        history = SalesHistory.objects.get(
            id=history_id,
            project_company=project_company
        )
        
        if request.method == 'GET':
            return Response({
                'id': history.id,
                'status': history.status,
                'status_date': history.status_date,
                'staff_name': history.staff_name,
                'notes': history.notes,
                'created_at': history.created_at,
            })
        
        elif request.method == 'PUT':
            history.status = request.data.get('status', history.status)
            history.status_date = request.data.get('status_date', history.status_date)
            history.staff_name = request.data.get('staff_name', history.staff_name)
            history.notes = request.data.get('notes', history.notes)
            history.save()
            
            return Response({
                'id': history.id,
                'status': history.status,
                'status_date': history.status_date,
                'staff_name': history.staff_name,
                'notes': history.notes,
                'created_at': history.created_at,
            })
        
        elif request.method == 'DELETE':
            history.delete()
            return Response({'message': '営業履歴を削除しました'}, status=status.HTTP_204_NO_CONTENT)
            
    except ProjectCompany.DoesNotExist:
        return Response({'error': '営業先企業が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
    except SalesHistory.DoesNotExist:
        return Response({'error': '営業履歴が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
