from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from companies.models import Company
from masters.models import Industry


class IndustryFilterTestCase(TestCase):
    """業界フィルターのテストケース"""

    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # マスターデータのセットアップ
        # 業界カテゴリ「コンサルティング・専門サービス」
        self.consulting_category = Industry.objects.create(
            name="コンサルティング・専門サービス",
            is_category=True,
            is_active=True,
            display_order=5
        )
        # 子業界（業種）
        self.consulting_sub1 = Industry.objects.create(
            name="経営コンサルティング",
            is_category=False,
            is_active=True,
            parent_industry=self.consulting_category,
            display_order=1
        )
        self.consulting_sub2 = Industry.objects.create(
            name="会計、税務、法務、労務",
            is_category=False,
            is_active=True,
            parent_industry=self.consulting_category,
            display_order=2
        )

        # 業界カテゴリ「IT・マスコミ」
        self.it_category = Industry.objects.create(
            name="IT・マスコミ",
            is_category=True,
            is_active=True,
            display_order=4
        )
        # 子業界（業種）
        self.it_sub1 = Industry.objects.create(
            name="情報通信、インターネット",
            is_category=False,
            is_active=True,
            parent_industry=self.it_category,
            display_order=1
        )
        self.it_sub2 = Industry.objects.create(
            name="ソフトウェア、SI",
            is_category=False,
            is_active=True,
            parent_industry=self.it_category,
            display_order=2
        )

        # テストデータの作成
        # コンサルティング関連
        Company.objects.create(
            name="テストコンサル会社1",
            industry="経営コンサルティング"
        )
        Company.objects.create(
            name="テストコンサル会社2",
            industry="会計、税務、法務、労務"
        )
        Company.objects.create(
            name="テストコンサル会社3",
            industry="経営コンサル"  # 表記の違い
        )

        # IT関連
        Company.objects.create(
            name="テストIT会社1",
            industry="情報通信、インターネット"
        )
        Company.objects.create(
            name="テストIT会社2",
            industry="ソフトウェア、SI"
        )

        # その他
        Company.objects.create(
            name="テスト製造会社",
            industry="製造業"
        )

    def test_filter_by_consulting_category(self):
        """業界カテゴリ「コンサルティング・専門サービス」で検索"""
        response = self.client.get('/api/v1/companies/', {
            'industry': 'コンサルティング・専門サービス'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', [])
        self.assertGreater(len(results), 0, "検索結果が0件です")
        
        # コンサルティング関連の企業が含まれていることを確認
        company_names = [c['name'] for c in results]
        self.assertIn('テストコンサル会社1', company_names)
        self.assertIn('テストコンサル会社2', company_names)
        # 表記の違いでもマッチすることを確認
        self.assertIn('テストコンサル会社3', company_names)
        
        # 製造業の企業が含まれていないことを確認
        self.assertNotIn('テスト製造会社', company_names)

    def test_filter_by_it_category(self):
        """業界カテゴリ「IT・マスコミ」で検索"""
        response = self.client.get('/api/v1/companies/', {
            'industry': 'IT・マスコミ'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', [])
        self.assertGreater(len(results), 0, "検索結果が0件です")
        
        # IT関連の企業が含まれていることを確認
        company_names = [c['name'] for c in results]
        self.assertIn('テストIT会社1', company_names)
        self.assertIn('テストIT会社2', company_names)
        
        # コンサルティングの企業が含まれていないことを確認
        self.assertNotIn('テストコンサル会社1', company_names)

    def test_filter_by_sub_industry_directly(self):
        """業種名を直接指定して検索（後方互換性）"""
        response = self.client.get('/api/v1/companies/', {
            'industry': '経営コンサルティング'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', [])
        self.assertGreater(len(results), 0, "検索結果が0件です")
        
        company_names = [c['name'] for c in results]
        self.assertIn('テストコンサル会社1', company_names)

    def test_filter_by_multiple_categories(self):
        """複数の業界カテゴリで検索"""
        response = self.client.get('/api/v1/companies/', {
            'industry': ['コンサルティング・専門サービス', 'IT・マスコミ']
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', [])
        self.assertGreater(len(results), 0, "検索結果が0件です")
        
        company_names = [c['name'] for c in results]
        # 両方のカテゴリの企業が含まれていることを確認
        self.assertIn('テストコンサル会社1', company_names)
        self.assertIn('テストIT会社1', company_names)
