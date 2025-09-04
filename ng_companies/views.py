from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def template_view(request):
    """NGリストCSVテンプレート取得（OpenAPI仕様準拠）"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="ng_companies_template.csv"'
    response.write('company_name,reason\n')
    response.write('例：株式会社サンプル,競合企業のため\n')
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def match_view(request):
    """NG企業マッチング実行（OpenAPI仕様準拠）"""
    client_id = request.data.get('client_id')
    project_id = request.data.get('project_id')
    
    return Response({
        'message': 'NG企業マッチング機能は開発中です',
        'matched_count': 0,
        'unmatched_count': 0
    })