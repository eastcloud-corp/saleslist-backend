from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from companies.models import Company
from projects.models import Project, ProjectCompany
from clients.models import Client
from companies.serializers import CompanyListSerializer
from projects.serializers import ProjectListSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """ダッシュボード統計データ取得"""
    
    total_companies = Company.objects.count()
    active_projects = Project.objects.filter(status='進行中').count()
    
    # 進行中プロジェクトに関連する企業数
    prospect_companies = ProjectCompany.objects.filter(
        project__status='進行中'
    ).values('company').distinct().count()
    
    # 成約済み企業数
    completed_deals = ProjectCompany.objects.filter(
        status='成約'
    ).count()
    
    return Response({
        'totalCompanies': total_companies,
        'activeProjects': active_projects,
        'prospectCompanies': prospect_companies,
        'completedDeals': completed_deals
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_projects(request):
    """最近のプロジェクト取得"""
    limit = request.GET.get('limit', 5)
    
    recent_projects = Project.objects.select_related('client').order_by('-updated_at')[:limit]
    
    results = []
    for project in recent_projects:
        results.append({
            'id': project.id,
            'name': project.name,
            'status': project.status,
            'companies': project.project_companies.count(),
            'client_name': project.client.name,
            'updated_at': project.updated_at
        })
    
    return Response({
        'results': results
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_companies(request):
    """最近の企業取得"""
    limit = request.GET.get('limit', 5)
    
    recent_companies = Company.objects.order_by('-created_at')[:limit]
    
    results = []
    for company in recent_companies:
        # 最新の営業ステータスを取得
        latest_status = 'アクティブ'
        latest_project_company = ProjectCompany.objects.filter(
            company=company
        ).order_by('-updated_at').first()
        
        if latest_project_company:
            latest_status = latest_project_company.status
        
        results.append({
            'id': company.id,
            'name': company.name,
            'industry': company.industry,
            'status': latest_status,
            'created_at': company.created_at
        })
    
    return Response({
        'results': results
    })
