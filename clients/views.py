from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
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
        reason = request.data.get('reason', '')
        
        if not company_id or not company_name:
            return Response({
                'error': '企業IDと企業名は必須です'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from companies.models import Company
        
        # 企業が存在するか確認
        try:
            company = Company.objects.get(id=company_id)
            matched = True
        except Company.DoesNotExist:
            # 企業が見つからない場合はnull参照で登録
            company = None
            matched = False
        
        # 重複チェック
        existing = ClientNGCompany.objects.filter(
            client=client,
            company=company if company else None,
            company_name=company_name
        ).first()
        
        if existing:
            return Response({
                'error': 'この企業は既にNGリストに登録されています'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # NGリストに追加
        ng_company = ClientNGCompany.objects.create(
            client=client,
            company=company,
            company_name=company_name,
            reason=reason,
            matched=matched,
        )
        
        serializer = ClientNGCompanySerializer(ng_company)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
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
        """クライアント用利用可能企業一覧（OpenAPI仕様準拠）"""
        client = self.get_object()
        from companies.models import Company
        
        # グローバルNG企業とクライアントNG企業を除外
        available_companies = Company.objects.filter(is_global_ng=False)
        client_ng_company_ids = client.ng_companies.filter(
            matched=True
        ).values_list('company_id', flat=True)
        available_companies = available_companies.exclude(
            id__in=client_ng_company_ids
        )
        
        from companies.serializers import CompanyListSerializer
        serializer = CompanyListSerializer(available_companies, many=True)
        
        return Response({
            'count': available_companies.count(),
            'results': serializer.data
        })
    
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
            csv_data = uploaded_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_data))
            
            imported_count = 0
            for row in csv_reader:
                company_name = row.get('company_name', '').strip()
                ng_reason = row.get('ng_reason', '').strip()
                
                if company_name:
                    ClientNGCompany.objects.get_or_create(
                        client=client,
                        company_name=company_name,
                        defaults={
                            'ng_reason': ng_reason,
                            'manager_name': request.user.name,
                            'is_global_ng': False
                        }
                    )
                    imported_count += 1
            
            return Response({
                'message': f'{imported_count}件のNG企業を登録しました',
                'imported_count': imported_count,
                'matched_count': imported_count,
                'unmatched_count': 0
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
