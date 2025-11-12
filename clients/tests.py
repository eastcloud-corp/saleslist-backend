import csv
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from clients.models import Client, ClientNGCompany
from companies.models import Company
from projects.models import Project, ProjectCompany


class ClientNGImportTests(TestCase):
    """NGリストCSVインポートの挙動を検証するテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='tester@example.com',
            password='password123',
            username='tester@example.com',
            name='テストユーザー'
        )
        self.client_obj = Client.objects.create(name='テストクライアント')
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)

    def test_import_ng_companies_creates_and_updates_records(self):
        """CSVからマッチ済みと未マッチのNG企業を取り込み、件数を集計できる"""
        matched_company = Company.objects.create(name='マッチ企業', industry='IT')
        ClientNGCompany.objects.create(
            client=self.client_obj,
            company_name='既存企業',
            reason='旧理由',
            matched=False,
        )

        csv_content = "企業名,理由\nマッチ企業,営業対象外\n既存企業,重複登録\n"
        uploaded = SimpleUploadedFile(
            'ng_companies.csv',
            csv_content.encode('utf-8'),
            content_type='text/csv'
        )

        url = reverse('client-import-ng-companies', kwargs={'pk': self.client_obj.pk})
        response = self.api_client.post(url, {'file': uploaded}, format='multipart')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['imported_count'], 2)
        self.assertEqual(response.data['matched_count'], 1)
        self.assertEqual(response.data['unmatched_count'], 1)
        self.assertEqual(response.data['errors'], [])

        ng_records = ClientNGCompany.objects.filter(client=self.client_obj)
        self.assertEqual(ng_records.count(), 2)

        matched_record = ng_records.get(company_name='マッチ企業')
        self.assertTrue(matched_record.matched)
        self.assertEqual(matched_record.company_id, matched_company.id)
        self.assertEqual(matched_record.reason, '営業対象外')

        updated_record = ng_records.get(company_name='既存企業')
        self.assertFalse(updated_record.matched)
        self.assertEqual(updated_record.reason, '重複登録')

    def test_import_ng_companies_requires_file(self):
        """ファイル未指定の場合は400を返す"""
        url = reverse('client-import-ng-companies', kwargs={'pk': self.client_obj.pk})
        response = self.api_client.post(url, {}, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_import_ng_companies_without_header_returns_error(self):
        """ヘッダーの無いCSVはエラーとして扱われる"""
        uploaded = SimpleUploadedFile(
            'ng_companies.csv',
            ''.encode('utf-8'),
            content_type='text/csv'
        )

        url = reverse('client-import-ng-companies', kwargs={'pk': self.client_obj.pk})
        response = self.api_client.post(url, {'file': uploaded}, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'CSVのヘッダーが確認できません')

    def test_import_ng_companies_skips_rows_without_company_name(self):
        """企業名が空の行は取り込み対象外でエラーに記録される"""
        csv_content = "企業名,理由\n,理由なし\n有効企業,最新理由\n"
        uploaded = SimpleUploadedFile(
            'ng_companies.csv',
            csv_content.encode('utf-8-sig'),
            content_type='text/csv'
        )

        url = reverse('client-import-ng-companies', kwargs={'pk': self.client_obj.pk})
        response = self.api_client.post(url, {'file': uploaded}, format='multipart')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['imported_count'], 1)
        self.assertEqual(response.data['matched_count'], 0)
        self.assertEqual(response.data['unmatched_count'], 1)
        self.assertEqual(response.data['errors'], ['2行目: 企業名が入力されていません'])

        self.assertTrue(
            ClientNGCompany.objects.filter(
                client=self.client_obj,
                company_name='有効企業'
            ).exists()
        )

    def test_import_ng_companies_updates_existing_matched_record(self):
        """既存のマッチ済みNG企業に対して理由を更新できる"""
        matched_company = Company.objects.create(name='一致企業', industry='メディア')
        ng_record = ClientNGCompany.objects.create(
            client=self.client_obj,
            company_name='一致企業',
            company=matched_company,
            matched=True,
            reason='旧理由'
        )

        csv_content = "企業名,理由\n一致企業,新理由\n"
        uploaded = SimpleUploadedFile(
            'ng_companies.csv',
            csv_content.encode('utf-8'),
            content_type='text/csv'
        )

        url = reverse('client-import-ng-companies', kwargs={'pk': self.client_obj.pk})
        response = self.api_client.post(url, {'file': uploaded}, format='multipart')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['imported_count'], 1)
        self.assertEqual(response.data['matched_count'], 1)
        self.assertEqual(response.data['unmatched_count'], 0)
        self.assertEqual(response.data['errors'], [])

        ng_record.refresh_from_db()
        self.assertEqual(ng_record.company_id, matched_company.id)
        self.assertTrue(ng_record.matched)
        self.assertEqual(ng_record.reason, '新理由')


class ClientAvailableCompaniesTests(TestCase):
    """NG情報付き企業一覧取得のテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='viewer@example.com',
            password='password123',
            username='viewer@example.com',
            name='参照ユーザー'
        )
        self.client_obj = Client.objects.create(name='参照クライアント')
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)

        self.global_company = Company.objects.create(
            name='グローバルNG企業',
            industry='IT',
            is_global_ng=True
        )
        self.client_company = Company.objects.create(
            name='クライアントNG企業',
            industry='IT',
            is_global_ng=False
        )
        self.name_only_company = Company.objects.create(
            name='名前のみNG企業',
            industry='IT',
            is_global_ng=False
        )
        self.normal_company = Company.objects.create(
            name='通常企業',
            industry='IT',
            is_global_ng=False
        )

        ClientNGCompany.objects.create(
            client=self.client_obj,
            company=self.client_company,
            company_name=self.client_company.name,
            matched=True,
            reason='重複営業防止'
        )
        ClientNGCompany.objects.create(
            client=self.client_obj,
            company_name=self.name_only_company.name,
            matched=False,
            reason='外部リストNG'
        )

    def test_available_companies_includes_ng_metadata(self):
        """グローバルNGとクライアントNGの種別がレスポンスに含まれる"""
        url = reverse('client-available-companies', kwargs={'pk': self.client_obj.pk})
        response = self.api_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)

        results = response.data['results']
        self.assertGreaterEqual(len(results), 4)

        status_by_name = {item['name']: item['ng_status'] for item in results}

        global_status = status_by_name['グローバルNG企業']
        self.assertTrue(global_status['is_ng'])
        self.assertIn('global', global_status['types'])
        self.assertEqual(global_status['reasons'].get('global'), 'グローバルNG設定')

        client_status = status_by_name['クライアントNG企業']
        self.assertTrue(client_status['is_ng'])
        self.assertIn('client', client_status['types'])
        self.assertEqual(
            client_status['reasons']['client']['reason'],
            '重複営業防止'
        )
        self.assertEqual(client_status['reasons']['client']['client_id'], self.client_obj.id)

        name_only_status = status_by_name['名前のみNG企業']
        self.assertTrue(name_only_status['is_ng'])
        self.assertIn('client', name_only_status['types'])
        self.assertEqual(
            name_only_status['reasons']['client']['reason'],
            '外部リストNG'
        )

        normal_status = status_by_name['通常企業']
        self.assertFalse(normal_status['is_ng'])
        self.assertEqual(normal_status['types'], [])
        self.assertEqual(normal_status['reasons'], {})

    def test_available_companies_respects_page_size_param(self):
        """page_size クエリで取得件数を調整できる"""
        for index in range(120):
            Company.objects.create(
                name=f'追加企業{index}',
                industry='IT',
                is_global_ng=False,
            )

        url = reverse('client-available-companies', kwargs={'pk': self.client_obj.pk})
        response = self.api_client.get(f"{url}?page_size=120")

        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 120)

    def test_available_companies_supports_ordering_param(self):
        Company.objects.create(name='かきくけこ株式会社', industry='IT')
        Company.objects.create(name='あいうえお株式会社', industry='IT')
        Company.objects.create(name='さしすせそ株式会社', industry='IT')

        url = reverse('client-available-companies', kwargs={'pk': self.client_obj.pk})
        response = self.api_client.get(f"{url}?ordering=-name&page_size=5")

        self.assertEqual(response.status_code, 200)
        names = [item['name'] for item in response.data['results'][:3]]
        self.assertEqual(names, sorted(names, reverse=True))


class ClientExportCompaniesTests(TestCase):
    """クライアント企業CSVエクスポートのテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='exporter@example.com',
            password='password123',
            username='exporter@example.com',
            name='輸出ユーザー'
        )
        self.client_obj = Client.objects.create(name='CSVクライアント')
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)

        self.project = Project.objects.create(client=self.client_obj, name='案件A')
        self.company_a = Company.objects.create(name='企業A', industry='IT')
        self.company_b = Company.objects.create(name='企業B', industry='不動産')
        ProjectCompany.objects.create(project=self.project, company=self.company_a, status='未接触')
        ProjectCompany.objects.create(project=self.project, company=self.company_b, status='DM送信済み', is_active=False)

    def test_export_companies_returns_csv_content(self):
        url = reverse('client-export-companies', kwargs={'pk': self.client_obj.pk})
        response = self.api_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn(f'client_{self.client_obj.id}_companies.csv', response['Content-Disposition'])

        rows = list(csv.reader(io.StringIO(response.content.decode('utf-8'))))
        self.assertGreaterEqual(len(rows), 3)  # header + 2 data rows
        header = rows[0]
        self.assertIn('client_name', header)
        data_names = {row[4] for row in rows[1:]}
        self.assertIn('企業A', data_names)
        self.assertIn('企業B', data_names)


class ClientNGBulkAddTests(TestCase):
    """NGリスト一括追加APIのテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='bulk@example.com',
            password='password123',
            username='bulk@example.com',
            name='一括追加ユーザー'
        )
        self.client_obj = Client.objects.create(name='一括追加クライアント')
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)

        # テスト用企業を作成
        self.company_1 = Company.objects.create(name='企業1', industry='IT')
        self.company_2 = Company.objects.create(name='企業2', industry='IT')
        self.company_3 = Company.objects.create(name='企業3', industry='IT')
        self.company_duplicate = Company.objects.create(name='重複企業', industry='IT')
        self.non_existent_id = 99999

        # 事前に重複企業をNGリストに追加
        ClientNGCompany.objects.create(
            client=self.client_obj,
            company=self.company_duplicate,
            company_name=self.company_duplicate.name,
            matched=True,
            reason='既存理由',
            is_active=True
        )

    def test_bulk_add_ng_companies_success(self):
        """複数企業の一括追加が正常に動作する"""
        url = reverse('client-bulk-add-ng-companies', kwargs={'pk': self.client_obj.pk})
        payload = {
            'company_ids': [self.company_1.id, self.company_2.id, self.company_3.id],
            'reason': '一括追加テスト'
        }
        response = self.api_client.post(url, payload, format='json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['added_count'], 3)
        self.assertEqual(data['skipped_count'], 0)
        self.assertEqual(data['error_count'], 0)
        self.assertEqual(len(data['added']), 3)

        # データベースで確認
        ng_companies = ClientNGCompany.objects.filter(client=self.client_obj)
        self.assertEqual(ng_companies.count(), 4)  # 既存の1件 + 新規3件

        for company in [self.company_1, self.company_2, self.company_3]:
            ng_company = ng_companies.get(company_name=company.name)
            self.assertEqual(ng_company.company_id, company.id)
            self.assertTrue(ng_company.matched)
            self.assertEqual(ng_company.reason, '一括追加テスト')
            self.assertTrue(ng_company.is_active)

    def test_bulk_add_ng_companies_with_duplicates(self):
        """既にNGリストに登録されている企業はスキップされる"""
        url = reverse('client-bulk-add-ng-companies', kwargs={'pk': self.client_obj.pk})
        payload = {
            'company_ids': [self.company_1.id, self.company_duplicate.id, self.company_2.id],
            'reason': '重複テスト'
        }
        response = self.api_client.post(url, payload, format='json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['added_count'], 2)  # company_1, company_2
        self.assertEqual(data['skipped_count'], 1)  # company_duplicate
        self.assertEqual(data['error_count'], 0)
        self.assertEqual(len(data['added']), 2)
        self.assertEqual(len(data['skipped']), 1)
        self.assertEqual(data['skipped'][0]['company_id'], self.company_duplicate.id)
        self.assertEqual(data['skipped'][0]['reason'], '既にNGリストに登録されています')

    def test_bulk_add_ng_companies_with_nonexistent_ids(self):
        """存在しない企業IDはエラーとして記録される"""
        url = reverse('client-bulk-add-ng-companies', kwargs={'pk': self.client_obj.pk})
        payload = {
            'company_ids': [self.company_1.id, self.non_existent_id, self.company_2.id],
            'reason': 'エラーテスト'
        }
        response = self.api_client.post(url, payload, format='json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['added_count'], 2)  # company_1, company_2
        self.assertEqual(data['skipped_count'], 0)
        self.assertEqual(data['error_count'], 1)  # non_existent_id
        self.assertEqual(len(data['errors']), 1)
        self.assertEqual(data['errors'][0]['company_id'], self.non_existent_id)
        self.assertIn('見つかりません', data['errors'][0]['error'])

    def test_bulk_add_ng_companies_requires_company_ids(self):
        """company_idsが必須であることを確認"""
        url = reverse('client-bulk-add-ng-companies', kwargs={'pk': self.client_obj.pk})
        
        # company_idsが無い場合
        response = self.api_client.post(url, {'reason': 'テスト'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

        # company_idsが空配列の場合
        response = self.api_client.post(url, {'company_ids': [], 'reason': 'テスト'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

        # company_idsが配列でない場合
        response = self.api_client.post(url, {'company_ids': 'not-an-array', 'reason': 'テスト'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_bulk_add_ng_companies_transaction_rollback(self):
        """トランザクションの整合性を確認（部分的失敗でも追加されたものは保持される）"""
        url = reverse('client-bulk-add-ng-companies', kwargs={'pk': self.client_obj.pk})
        payload = {
            'company_ids': [self.company_1.id, self.non_existent_id, self.company_2.id],
            'reason': 'トランザクションテスト'
        }
        response = self.api_client.post(url, payload, format='json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['added_count'], 2)
        self.assertEqual(data['error_count'], 1)

        # 正常に追加された企業はデータベースに存在する
        self.assertTrue(
            ClientNGCompany.objects.filter(
                client=self.client_obj,
                company=self.company_1
            ).exists()
        )
        self.assertTrue(
            ClientNGCompany.objects.filter(
                client=self.client_obj,
                company=self.company_2
            ).exists()
        )

    def test_bulk_add_ng_companies_without_reason(self):
        """理由が無くても追加できる"""
        url = reverse('client-bulk-add-ng-companies', kwargs={'pk': self.client_obj.pk})
        payload = {
            'company_ids': [self.company_1.id]
        }
        response = self.api_client.post(url, payload, format='json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['added_count'], 1)

        ng_company = ClientNGCompany.objects.get(client=self.client_obj, company=self.company_1)
        self.assertEqual(ng_company.reason, '')
