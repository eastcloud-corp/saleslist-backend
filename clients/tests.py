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
