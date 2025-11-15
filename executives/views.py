from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from companies.models import Executive, Company
from companies.serializers import ExecutiveSerializer


class ExecutiveViewSet(viewsets.ModelViewSet):
    """役員ViewSet（OpenAPI仕様準拠）"""
    queryset = Executive.objects.all()
    serializer_class = ExecutiveSerializer
    filter_backends = []
    ordering = ['-created_at']
    
    @action(detail=False, methods=['post'], url_path='import_csv')
    def import_csv(self, request):
        """役員CSVインポート"""
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
                company_name = row.get('company_name', '').strip()
                name = row.get('name', '').strip()
                
                if company_name and name:
                    try:
                        company = Company.objects.get(name=company_name)
                        Executive.objects.get_or_create(
                            company=company,
                            name=name,
                            defaults={
                                'position': row.get('position', ''),
                                'facebook_url': row.get('facebook_url', ''),
                                'other_sns_url': row.get('other_sns_url', ''),
                                'direct_email': row.get('direct_email', ''),
                                'notes': row.get('notes', ''),
                            }
                        )
                        imported_count += 1
                    except Company.DoesNotExist:
                        continue
            
            return Response({
                'message': f'{imported_count}件の役員を登録しました',
                'imported_count': imported_count
            })
            
        except Exception as e:
            return Response({
                'error': f'インポートに失敗しました: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='export_csv')
    def export_csv(self, request):
        """役員CSVエクスポート"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="executives.csv"'
        
        # BOMを追加してExcelで正しく日本語を表示
        response.write('\ufeff')
        import csv
        writer = csv.writer(response)
        writer.writerow(['company_name', 'name', 'position', 'facebook_url', 'other_sns_url', 'direct_email', 'notes'])
        
        for executive in Executive.objects.select_related('company').all():
            writer.writerow([
                executive.company.name,
                executive.name,
                executive.position,
                executive.facebook_url,
                executive.other_sns_url,
                executive.direct_email,
                executive.notes,
            ])
        
        return response