from datetime import date, timedelta
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from unittest.mock import patch

from accounts.models import User
from clients.models import Client, ClientNGCompany
from companies.models import Company
from masters.models import (
    ProjectProgressStatus,
    ServiceType,
    MediaType,
    RegularMeetingStatus,
    ListAvailability,
    ListImportSource,
)
from projects.serializers import (
    ProjectManagementListSerializer,
    ProjectManagementUpdateSerializer,
    ProjectSnapshotSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    ProjectManagementDetailSerializer,
    ProjectCreateSerializer,
)
from projects.models import (
    Project,
    ProjectCompany,
    ProjectEditLock,
    ProjectSnapshot,
    PageEditLock,
    ProjectNGCompany,
)
from projects.views import ProjectViewSet


class ProjectBulkPartialUpdateTests(TestCase):
    """一括差分更新APIのユニットテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='project-owner@example.com',
            password='password123',
            username='project-owner@example.com',
            name='案件オーナー'
        )
        self.client_obj = Client.objects.create(name='案件クライアント')
        self.project = Project.objects.create(
            client=self.client_obj,
            name='案件A',
            appointment_count=1,
            situation='初期メモ'
        )
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)

    def test_bulk_partial_update_updates_project_and_creates_snapshot(self):
        """有効な差分更新は案件を更新しスナップショットを保存する"""
        url = reverse('project-bulk-partial-update')
        payload = {
            'items': [
                {
                    'project_id': self.project.id,
                    'data': {
                        'appointment_count': 5,
                        'situation': '更新後メモ',
                    },
                    'reason': 'テスト更新',
                }
            ]
        }

        response = self.api_client.post(url, payload, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['updated_count'], 1)
        self.assertEqual(len(response.data['snapshots']), 1)

        self.project.refresh_from_db()
        self.assertEqual(self.project.appointment_count, 5)
        self.assertEqual(self.project.situation, '更新後メモ')

        snapshot = ProjectSnapshot.objects.get(project=self.project)
        self.assertIn('appointment_count', snapshot.reason)
        self.assertIn('situation', snapshot.reason)
        self.assertEqual(snapshot.data['project']['appointment_count'], 1)
        self.assertEqual(snapshot.data['project']['situation'], '初期メモ')

    def test_bulk_partial_update_returns_error_when_locked_by_other_user(self):
        """他ユーザーがロック中の場合は更新せずエラーを返す"""
        other_user = User.objects.create_user(
            email='locker@example.com',
            password='password123',
            username='locker@example.com',
            name='ロックユーザー'
        )
        ProjectEditLock.objects.create(
            project=self.project,
            user=other_user,
            expires_at=timezone.now() + timedelta(minutes=30)
        )

        url = reverse('project-bulk-partial-update')
        payload = {
            'items': [
                {
                    'project_id': self.project.id,
                    'data': {
                        'appointment_count': 3,
                    }
                }
            ]
        }

        response = self.api_client.post(url, payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['updated_count'], 0)
        self.assertIn(str(self.project.id), response.data['errors'])
        self.assertIn('ロックユーザー', response.data['errors'][str(self.project.id)])

        self.project.refresh_from_db()
        self.assertEqual(self.project.appointment_count, 1)
        self.assertEqual(ProjectSnapshot.objects.filter(project=self.project).count(), 0)


class ProjectBulkUpdateTests(TestCase):
    """一括更新APIのユニットテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='bulk-owner@example.com',
            password='password123',
            username='bulk-owner@example.com',
            name='一括オーナー'
        )
        self.client_obj = Client.objects.create(name='一括クライアント')
        self.project1 = Project.objects.create(
            client=self.client_obj,
            name='案件B',
            situation='初期メモ1',
            reply_count=0
        )
        self.project2 = Project.objects.create(
            client=self.client_obj,
            name='案件C',
            situation='初期メモ2',
            reply_count=1
        )
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)

    def test_bulk_update_updates_multiple_projects_and_snapshots(self):
        """複数案件をまとめて更新し、スナップショットが作成される"""
        url = reverse('project-bulk-update')
        payload = {
            'project_ids': [self.project1.id, self.project2.id],
            'update_data': {
                'situation': '更新メモ',
                'reply_count': 5,
            },
            'reason': '一括更新テスト'
        }

        response = self.api_client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['updated_count'], 2)
        self.assertEqual(len(response.data['snapshots']), 2)

        self.project1.refresh_from_db()
        self.project2.refresh_from_db()
        self.assertEqual(self.project1.situation, '更新メモ')
        self.assertEqual(self.project1.reply_count, 5)
        self.assertEqual(self.project2.situation, '更新メモ')
        self.assertEqual(self.project2.reply_count, 5)

        snapshots = ProjectSnapshot.objects.filter(project__in=[self.project1, self.project2])
        self.assertEqual(snapshots.count(), 2)
        original_values = {
            self.project1.id: ('初期メモ1', 0),
            self.project2.id: ('初期メモ2', 1),
        }
        for snapshot in snapshots:
            self.assertIn('reply_count', snapshot.reason)
            self.assertIn('situation', snapshot.reason)
            situation, reply = original_values[snapshot.project_id]
            self.assertEqual(snapshot.data['project']['situation'], situation)
            self.assertEqual(snapshot.data['project']['reply_count'], reply)

    def test_bulk_update_conflict_when_locked(self):
        """他ユーザーがロック中の場合は409を返す"""
        other_user = User.objects.create_user(
            email='bulk-locker@example.com',
            password='password123',
            username='bulk-locker@example.com',
            name='一括ロックユーザー'
        )
        ProjectEditLock.objects.create(
            project=self.project1,
            user=other_user,
            expires_at=timezone.now() + timedelta(minutes=10)
        )

        url = reverse('project-bulk-update')
        payload = {
            'project_ids': [self.project1.id],
            'update_data': {'situation': 'ロック中更新'},
        }

        response = self.api_client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.data['success'])
        self.assertIn('error', response.data)
        self.project1.refresh_from_db()
        self.assertEqual(self.project1.situation, '初期メモ1')


class ProjectSnapshotRestoreTests(TestCase):
    """スナップショット復元APIのユニットテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='restore-user@example.com',
            password='password123',
            username='restore-user@example.com',
            name='スナップショット復元ユーザー'
        )
        self.client_obj = Client.objects.create(name='復元クライアント')
        self.project = Project.objects.create(
            client=self.client_obj,
            name='復元案件',
            appointment_count=1,
            situation='初期メモ'
        )
        self.company = Company.objects.create(name='復元企業', industry='IT')
        self.project_company = ProjectCompany.objects.create(
            project=self.project,
            company=self.company,
            status='未接触'
        )
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)

    def test_restore_snapshot_recovers_project_and_companies(self):
        """スナップショットから案件と関連企業の状態を復元できる"""
        bulk_partial_url = reverse('project-bulk-partial-update')
        payload = {
            'items': [
                {
                    'project_id': self.project.id,
                    'data': {
                        'appointment_count': 4,
                        'situation': '更新後メモ',
                    },
                    'reason': '初回更新'
                }
            ]
        }

        response = self.api_client.post(bulk_partial_url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        snapshot_id = response.data['snapshots'][0]['snapshot_id']

        # 現在の状態をさらに変更
        self.project.appointment_count = 9
        self.project.situation = '最終メモ'
        self.project.save()
        self.project_company.status = 'DM送信済み'
        self.project_company.save()

        restore_url = reverse('project-restore-snapshot', kwargs={
            'pk': self.project.id,
            'snapshot_id': snapshot_id
        })
        restore_response = self.api_client.post(restore_url)

        self.assertEqual(restore_response.status_code, 200)
        self.assertTrue(restore_response.data['success'])
        self.assertEqual(restore_response.data['restored_snapshot_id'], snapshot_id)

        self.project.refresh_from_db()
        self.project_company.refresh_from_db()
        self.assertEqual(self.project.appointment_count, 1)
        self.assertEqual(self.project.situation, '初期メモ')
        self.assertEqual(self.project_company.status, '未接触')

        snapshots = ProjectSnapshot.objects.filter(project=self.project).order_by('id')
        self.assertEqual(snapshots.count(), 3)
        sources = [s.source for s in snapshots]
        self.assertIn('bulk_edit', sources)
        self.assertIn('undo', sources)
        self.assertIn('restore', sources)


class ProjectAddCompaniesTests(TestCase):
    """案件への企業追加APIのユニットテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='adder@example.com',
            password='password123',
            username='adder@example.com',
            name='追加ユーザー'
        )
        self.client_obj = Client.objects.create(name='追加クライアント')
        self.project = Project.objects.create(
            client=self.client_obj,
            name='追加案件'
        )
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)

        self.normal_company = Company.objects.create(name='通常企業', industry='IT')
        self.other_company = Company.objects.create(name='別企業', industry='IT')
        self.global_company = Company.objects.create(name='グローバルNG企業', industry='IT', is_global_ng=True)
        self.client_company = Company.objects.create(name='クライアントNG企業', industry='IT')
        self.name_only_company = Company.objects.create(name='名前のみ参照', industry='IT')

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
            reason='外部データ'
        )

    def test_add_companies_adds_non_ng_companies(self):
        """NGではない企業は案件に追加される"""
        url = reverse('project-add-companies', kwargs={'pk': self.project.id})
        response = self.api_client.post(url, {'company_ids': [self.normal_company.id, self.other_company.id]}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['added_count'], 2)
        self.assertEqual(response.data['errors'], [])

        companies = ProjectCompany.objects.filter(project=self.project).order_by('company__name')
        self.assertEqual(companies.count(), 2)
        names = list(companies.values_list('company__name', flat=True))
        self.assertListEqual(names, ['別企業', '通常企業'])
        self.assertTrue(ProjectCompany.objects.filter(project=self.project, company=self.normal_company).exists())
        self.assertTrue(ProjectCompany.objects.filter(project=self.project, company=self.other_company).exists())

    def test_add_companies_skips_ng_and_missing_entries(self):
        """NG企業や存在しない企業は追加されずエラーリストに含まれる"""
        url = reverse('project-add-companies', kwargs={'pk': self.project.id})
        response = self.api_client.post(url, {
            'company_ids': [
                self.global_company.id,
                self.client_company.id,
                self.name_only_company.id,
                999999,
            ]
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['added_count'], 0)
        self.assertEqual(len(response.data['errors']), 4)
        error_text = ' '.join(response.data['errors'])
        self.assertIn('グローバルNG企業', error_text)
        self.assertIn('クライアントNG企業', error_text)
        self.assertIn('名前のみ参照', error_text)
        self.assertIn('企業ID 999999 が見つかりません', error_text)

        self.assertEqual(ProjectCompany.objects.filter(project=self.project).count(), 0)

    def test_add_companies_requires_company_ids(self):
        """company_ids が指定されていない場合は400を返す"""
        url = reverse('project-add-companies', kwargs={'pk': self.project.id})
        response = self.api_client.post(url, {}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('企業IDが指定されていません', response.data['error'])


class ProjectPageLockTests(TestCase):
    """ページロックAPIのユニットテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='pagelock@example.com',
            password='password123',
            username='pagelock@example.com',
            name='ページロックユーザー'
        )
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)
        self.url = reverse('project-acquire-page-lock')

    def test_acquire_page_lock_creates_new_lock(self):
        """ロック未取得の場合は新規ロックを作成する"""
        response = self.api_client.post(self.url, {
            'page': 1,
            'page_size': 25,
            'filter_hash': 'hash-1'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        locked_until = parse_datetime(response.data['locked_until'])
        self.assertIsNotNone(locked_until)

        lock = PageEditLock.objects.get(page_number=1, filter_hash='hash-1')
        self.assertEqual(lock.user, self.user)

    def test_acquire_page_lock_extends_existing_lock_for_same_user(self):
        """同一ユーザーが再取得した場合はロック期限を更新する"""
        self.api_client.post(self.url, {
            'page': 2,
            'page_size': 25,
            'filter_hash': 'hash-2'
        }, format='json')
        lock = PageEditLock.objects.get(page_number=2, filter_hash='hash-2')
        original_expires = lock.expires_at

        response = self.api_client.post(self.url, {
            'page': 2,
            'page_size': 25,
            'filter_hash': 'hash-2'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        lock.refresh_from_db()
        self.assertGreater(lock.expires_at, original_expires)
        self.assertEqual(lock.user, self.user)
        self.assertTrue(response.data['success'])

    def test_acquire_page_lock_conflict_with_other_user(self):
        """別ユーザーが保持している場合は409を返す"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='password123',
            username='other@example.com',
            name='他ユーザー'
        )
        PageEditLock.objects.create(
            user=other_user,
            page_number=3,
            page_size=20,
            filter_hash='hash-3',
            expires_at=timezone.now() + timedelta(minutes=30)
        )

        response = self.api_client.post(self.url, {
            'page': 3,
            'page_size': 20,
            'filter_hash': 'hash-3'
        }, format='json')

        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['locked_by_name'], '他ユーザー')
        lock = PageEditLock.objects.get(page_number=3, filter_hash='hash-3')
        self.assertEqual(lock.user, other_user)

    def test_release_page_lock_removes_existing_lock(self):
        """DELETEメソッドでロックが解除される"""
        PageEditLock.objects.create(
            user=self.user,
            page_number=4,
            page_size=20,
            filter_hash='hash-4',
            expires_at=timezone.now() + timedelta(minutes=30)
        )

        response = self.api_client.delete(f"{self.url}?page=4&filter_hash=hash-4")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertFalse(PageEditLock.objects.filter(page_number=4, filter_hash='hash-4').exists())


class ProjectAvailableCompaniesTests(TestCase):
    """案件向け利用可能企業一覧APIのテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='available@example.com',
            password='password123',
            username='available@example.com',
            name='利用可能ユーザー'
        )
        self.client_obj = Client.objects.create(name='案件クライアント')
        self.project = Project.objects.create(client=self.client_obj, name='案件D')
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)

    def test_available_companies_paginated_includes_ng_status(self):
        """ページング時にグローバル/クライアントNGが整形される"""
        existing_company = Company.objects.create(name='既存企業', industry='IT')
        ProjectCompany.objects.create(project=self.project, company=existing_company)

        # ページサイズ(50)を超える企業を作成
        filler_companies = [
            Company.objects.create(name=f'フィラー企業{i:03d}', industry='IT')
            for i in range(55)
        ]

        global_company = Company.objects.create(name='グローバル対象企業', industry='IT', is_global_ng=True)
        client_match_company = Company.objects.create(name='クライアント一致企業', industry='IT')
        client_name_only_company = Company.objects.create(name='クライアント名称企業', industry='IT')

        ClientNGCompany.objects.create(
            client=self.client_obj,
            company=client_match_company,
            company_name=client_match_company.name,
            matched=True,
            reason='重複営業防止'
        )
        ClientNGCompany.objects.create(
            client=self.client_obj,
            company_name=client_name_only_company.name,
            matched=True,
            reason='外部データ'
        )

        url = reverse('project-available-companies', kwargs={'pk': self.project.id})
        response = self.api_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        expected_count = Company.objects.exclude(id=existing_company.id).count()
        self.assertEqual(response.data['count'], expected_count)
        self.assertEqual(len(response.data['results']), 50)

        status_by_name = {
            item['name']: item.get('ng_status')
            for item in response.data['results']
        }

        global_status = status_by_name['グローバル対象企業']
        self.assertTrue(global_status['is_ng'])
        self.assertIn('global', global_status['types'])
        self.assertEqual(global_status['reasons']['global'], 'グローバルNG設定')

        match_status = status_by_name['クライアント一致企業']
        self.assertTrue(match_status['is_ng'])
        self.assertIn('client', match_status['types'])
        self.assertEqual(match_status['reasons']['client']['id'], self.client_obj.id)
        self.assertEqual(match_status['reasons']['client']['reason'], '重複営業防止')

        name_only_status = status_by_name['クライアント名称企業']
        self.assertTrue(name_only_status['is_ng'])
        self.assertIn('client', name_only_status['types'])
        self.assertEqual(name_only_status['reasons']['client']['reason'], '外部データ')

        self.assertTrue(any(not item['ng_status']['is_ng'] for item in response.data['results']))

    def test_available_companies_without_pagination_excludes_existing(self):
        """ページングが発生しない場合でも既存企業は除外される"""
        existing_company = Company.objects.create(name='既存企業', industry='IT')
        ProjectCompany.objects.create(project=self.project, company=existing_company)

        normal_company = Company.objects.create(name='新規企業', industry='IT')

        url = reverse('project-available-companies', kwargs={'pk': self.project.id})
        response = self.api_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], '新規企業')


class ProjectBulkUpdateStatusTests(TestCase):
    """案件企業の一括ステータス更新テスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='bulk-status@example.com',
            password='password123',
            username='bulk-status@example.com',
            name='一括ステータスユーザー'
        )
        self.client_obj = Client.objects.create(name='ステータスクライアント')
        self.project = Project.objects.create(client=self.client_obj, name='ステータス案件')
        self.company1 = Company.objects.create(name='対象企業1', industry='IT')
        self.company2 = Company.objects.create(name='対象企業2', industry='IT')
        self.company3 = Company.objects.create(name='対象外企業', industry='IT')
        ProjectCompany.objects.create(project=self.project, company=self.company1, status='未接触')
        ProjectCompany.objects.create(project=self.project, company=self.company2, status='未接触')
        ProjectCompany.objects.create(project=self.project, company=self.company3, status='未接触')
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)

    def test_bulk_update_status_updates_selected_companies(self):
        url = reverse('project-bulk-update-status', kwargs={'pk': self.project.id})
        payload = {
            'company_ids': [self.company1.id, self.company2.id],
            'status': 'DM送信済み'
        }

        response = self.api_client.post(url, payload, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['updated_count'], 2)
        self.assertEqual(response.data['status'], 'DM送信済み')

        self.assertEqual(ProjectCompany.objects.get(project=self.project, company=self.company1).status, 'DM送信済み')
        self.assertEqual(ProjectCompany.objects.get(project=self.project, company=self.company2).status, 'DM送信済み')
        self.assertEqual(ProjectCompany.objects.get(project=self.project, company=self.company3).status, '未接触')

    def test_bulk_update_status_requires_parameters(self):
        url = reverse('project-bulk-update-status', kwargs={'pk': self.project.id})
        response = self.api_client.post(url, {'company_ids': []}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('company_ids と status が必要です', response.data['error'])


class ProjectImportExportCsvTests(TestCase):
    """案件CSVインポート/エクスポートのテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='csv@example.com',
            password='password123',
            username='csv@example.com',
            name='CSVユーザー'
        )
        self.client_obj = Client.objects.create(name='CSVクライアント')
        self.project = Project.objects.create(client=self.client_obj, name='CSV案件')
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)

    def test_import_csv_creates_or_updates_projects(self):
        Project.objects.create(client=self.client_obj, name='CSV案件A', description='旧説明', manager='旧担当', status='進行中')
        csv_content = f'name,description,manager,status,client_id\nCSV案件A,新説明,新担当,完了,{self.client_obj.id}\nCSV案件B,説明B,担当者B,進行中,{self.client_obj.id}\n'
        uploaded = SimpleUploadedFile('projects.csv', csv_content.encode('utf-8'), content_type='text/csv')
        url = reverse('project-import-csv')
        response = self.api_client.post(url, {'file': uploaded}, format='multipart')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['imported_count'], 2)
        self.assertEqual(response.data['created_count'], 1)
        self.assertEqual(response.data['updated_count'], 1)
        self.assertEqual(response.data['errors'], [])

        updated_project = Project.objects.get(name='CSV案件A')
        self.assertEqual(updated_project.description, '新説明')
        self.assertEqual(updated_project.manager, '新担当')
        self.assertEqual(updated_project.status, '完了')

        created_project = Project.objects.get(name='CSV案件B')
        self.assertEqual(created_project.description, '説明B')
        self.assertEqual(created_project.manager, '担当者B')
        self.assertEqual(created_project.status, '進行中')

    def test_import_csv_requires_file(self):
        url = reverse('project-import-csv')
        response = self.api_client.post(url, {}, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertIn('CSVファイルが必要です', response.data['error'])

    def test_export_csv_returns_csv_content(self):
        company = Company.objects.create(name='輸出企業', industry='IT')
        ProjectCompany.objects.create(
            project=self.project,
            company=company,
            status='DM送信済み',
            notes='メモ',
        )

        url = reverse('project-export-csv', kwargs={'pk': self.project.id})
        response = self.api_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment; filename="project_', response['Content-Disposition'])

        content = response.content.decode('utf-8')
        self.assertIn('輸出企業', content)
        self.assertIn('DM送信済み', content)


class ProjectSerializerUnitTests(TestCase):
    """シリアライザー周りのユニットテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='serializer@example.com',
            password='password123',
            username='serializer@example.com',
            name='シリアライザー利用者'
        )
        self.client_obj = Client.objects.create(name='シリアライザークライアント')

        self.progress_status = ProjectProgressStatus.objects.create(name='進行中', display_order=1)
        self.progress_status_new = ProjectProgressStatus.objects.create(name='完了', display_order=2)
        self.service_type = ServiceType.objects.create(name='コンサル', display_order=1)
        self.media_type = MediaType.objects.create(name='LINE', display_order=1)
        self.regular_status = RegularMeetingStatus.objects.create(name='予定あり', display_order=1)
        self.list_availability = ListAvailability.objects.create(name='あり', display_order=1)
        self.list_import_source = ListImportSource.objects.create(name='社内', display_order=1)

        self.project = Project.objects.create(
            client=self.client_obj,
            name='シリアライザー案件',
            progress_status=self.progress_status,
            service_type=self.service_type,
            media_type=self.media_type,
            regular_meeting_status=self.regular_status,
            list_availability=self.list_availability,
            list_import_source=self.list_import_source,
            director='ディレクター',
            operator='オペレーター',
            sales_person='セールス',
            appointment_count=3,
            approval_count=2,
            reply_count=1,
            friends_count=4,
            situation='進行中',
        )

        self.company = Company.objects.create(name='シリアライズ企業', industry='IT')
        ProjectCompany.objects.create(project=self.project, company=self.company)

    def test_management_list_serializer_lock_fields(self):
        lock = ProjectEditLock.objects.create(
            project=self.project,
            user=self.user,
            expires_at=timezone.now() + timedelta(minutes=30)
        )
        self.project.project_company_count = 99

        helper_serializer = ProjectManagementListSerializer()
        self.assertTrue(helper_serializer.get_is_locked(self.project))
        self.assertEqual(helper_serializer.get_locked_by(self.project), self.user.id)
        self.assertEqual(helper_serializer.get_locked_by_name(self.project), self.user.name)

        data = ProjectManagementListSerializer(self.project).data
        self.assertTrue(data['is_locked'])
        self.assertEqual(data['locked_by'], self.user.id)
        self.assertEqual(data['locked_by_name'], self.user.name)
        self.assertIsNotNone(data['locked_until'])
        self.assertEqual(data['company_count'], 99)

        lock.expires_at = timezone.now() - timedelta(minutes=1)
        lock.save(update_fields=['expires_at'])
        stale_data = ProjectManagementListSerializer(self.project).data
        self.assertFalse(stale_data['is_locked'])
        self.assertIsNone(stale_data['locked_by'])
        self.assertIsNone(stale_data['locked_by_name'])
        self.assertIsNone(stale_data['locked_until'])
        self.assertFalse(helper_serializer.get_is_locked(self.project))
        self.assertIsNone(helper_serializer.get_locked_until(self.project))

        delattr(self.project, 'project_company_count')
        fallback_count = ProjectManagementListSerializer().get_company_count(self.project)
        self.assertEqual(fallback_count, 1)

    def test_management_update_serializer_sets_foreign_keys(self):
        self.project.refresh_from_db()
        payload = {
            'progress_status_id': self.progress_status_new.id,
            'service_type_id': self.service_type.id,
            'media_type_id': self.media_type.id,
            'regular_meeting_status_id': self.regular_status.id,
            'list_availability_id': self.list_availability.id,
            'list_import_source_id': self.list_import_source.id,
            'appointment_count': 10,
        }
        serializer = ProjectManagementUpdateSerializer(
            self.project,
            data=payload,
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.project.refresh_from_db()
        self.assertEqual(self.project.progress_status, self.progress_status_new)
        self.assertEqual(self.project.appointment_count, 10)

    def test_management_update_serializer_accepts_null_foreign_key(self):
        payload = {'progress_status_id': None}
        serializer = ProjectManagementUpdateSerializer(
            self.project,
            data=payload,
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.project.refresh_from_db()
        self.assertIsNone(self.project.progress_status)

    def test_management_update_serializer_invalid_foreign_key_raises(self):
        serializer = ProjectManagementUpdateSerializer(
            self.project,
            data={'service_type_id': 999},
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaises(serializers.ValidationError):
            serializer.save()

    def test_snapshot_serializer_outputs_changed_fields(self):
        snapshot = ProjectSnapshot.objects.create(
            project=self.project,
            data={'project': {'name': 'シリアライザー案件', 'progress_status': '進行中', 'appointment_count': 3}},
            created_by=self.user,
            reason='Bulk update: appointment_count, progress_status',
            source='bulk_edit'
        )

        data = ProjectSnapshotSerializer(snapshot).data
        self.assertEqual(data['source_label'], '一括編集')
        self.assertEqual(data['changed_fields'], ['appointment_count', 'progress_status'])
        overview = data['project_overview']
        self.assertIn('name', overview)
        self.assertEqual(overview['appointment_count'], 3)

    def test_project_detail_serializer_returns_companies(self):
        serializer = ProjectDetailSerializer(self.project)
        data = serializer.data
        self.assertEqual(data['company_count'], 1)
        self.assertEqual(data['companies'][0]['company_name'], 'シリアライズ企業')

        management_detail = ProjectManagementDetailSerializer(self.project)
        detail_data = management_detail.data
        self.assertEqual(detail_data['company_count'], 1)
        self.assertEqual(detail_data['companies'][0]['company_name'], 'シリアライズ企業')

    def test_project_list_serializer_uses_count(self):
        serializer = ProjectListSerializer(self.project)
        self.assertEqual(serializer.data['company_count'], 1)


class ProjectViewSetAdditionalTests(TestCase):
    """ProjectViewSet の未カバー分岐を網羅する追加テスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='viewset@example.com',
            password='password123',
            username='viewset@example.com',
            name='ビューセット利用者'
        )
        self.client_obj = Client.objects.create(name='追加テストクライアント')
        self.project = Project.objects.create(client=self.client_obj, name='追加案件')
        self.company = Company.objects.create(name='追加企業', industry='IT')
        self.project_company = ProjectCompany.objects.create(project=self.project, company=self.company)
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)
        self.factory = APIRequestFactory()

    def test_list_endpoint_logs_and_returns_projects(self):
        Project.objects.create(client=self.client_obj, name='別案件')
        view = ProjectViewSet.as_view({'get': 'list'})
        request = self.factory.get('/api/v1/projects/', {'management_mode': 'true', 'status': '進行中', 'page': '1'})
        force_authenticate(request, user=self.user)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)

    def test_log_activity_with_anonymous_user(self):
        drf_request = Request(self.factory.get('/api/v1/projects/'))
        drf_request.user = AnonymousUser()
        view = ProjectViewSet()
        view.request = drf_request
        view._log_activity(AnonymousUser(), 'test.log', extra='value')

    def test_get_serializer_class_switches_by_action(self):
        drf_request = Request(self.factory.get('/api/v1/projects/', {'management_mode': 'true'}))
        drf_request.user = self.user
        view = ProjectViewSet()
        view.request = drf_request

        view.action = 'retrieve'
        self.assertIs(view.get_serializer_class(), ProjectManagementDetailSerializer)
        view.action = 'create'
        self.assertIs(view.get_serializer_class(), ProjectCreateSerializer)
        view.action = 'update'
        self.assertIs(view.get_serializer_class(), ProjectManagementUpdateSerializer)
        view.action = 'list'
        self.assertIs(view.get_serializer_class(), ProjectManagementListSerializer)
        view.action = 'custom'
        self.assertIs(view.get_serializer_class(), ProjectListSerializer)

        drf_request_plain = Request(self.factory.get('/api/v1/projects/'))
        drf_request_plain.user = self.user
        view.request = drf_request_plain
        view.action = 'retrieve'
        self.assertIs(view.get_serializer_class(), ProjectDetailSerializer)
        view.action = 'update'
        self.assertIs(view.get_serializer_class(), ProjectDetailSerializer)
        view.action = 'list'
        self.assertIs(view.get_serializer_class(), ProjectListSerializer)

    def test_companies_action_returns_data(self):
        url = reverse('project-companies', kwargs={'pk': self.project.id})
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_ng_companies_action_returns_data(self):
        ProjectNGCompany.objects.create(project=self.project, company=self.company, reason='重複')
        url = reverse('project-ng-companies', kwargs={'pk': self.project.id})
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_available_companies_without_pagination(self):
        ProjectCompany.objects.all().delete()
        response = self.api_client.get(reverse('project-available-companies', kwargs={'pk': self.project.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_available_companies_without_pagination_branch(self):
        with patch.object(ProjectViewSet, 'paginate_queryset', return_value=None):
            response = self.api_client.get(reverse('project-available-companies', kwargs={'pk': self.project.id}))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data['count'], 0)

    def test_bulk_update_validation_errors(self):
        url = reverse('project-bulk-update')
        response = self.api_client.patch(url, {'project_ids': [], 'update_data': {}}, format='json')
        self.assertEqual(response.status_code, 400)

        response = self.api_client.patch(url, {'project_ids': [999], 'update_data': {'situation': '更新'}}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_bulk_partial_update_errors_and_multi_status(self):
        url = reverse('project-bulk-partial-update')
        response = self.api_client.post(url, {'items': []}, format='json')
        self.assertEqual(response.status_code, 400)

        other_project = Project.objects.create(client=self.client_obj, name='部分更新案件')
        payload = {
            'items': [
                {'project_id': other_project.id, 'data': {'situation': '更新'}, 'reason': 'テスト'},
                {'project_id': other_project.id, 'data': {}},
            ]
        }
        response = self.api_client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertTrue(response.data['success'])
        self.assertIsNotNone(response.data['errors'])

    def test_import_csv_handles_exceptions(self):
        csv_content = f'name,client_id\n案件X,{self.client_obj.id}\n'
        uploaded = SimpleUploadedFile('projects.csv', csv_content.encode('utf-8'), content_type='text/csv')
        with patch('projects.views.Project.objects.update_or_create', side_effect=Exception('boom')):
            response = self.api_client.post(reverse('project-import-csv'), {'file': uploaded}, format='multipart')
        self.assertEqual(response.status_code, 500)

    def test_import_csv_records_missing_fields(self):
        csv_content = 'name,client_id\n案件Z,\n'
        uploaded = SimpleUploadedFile('invalid.csv', csv_content.encode('utf-8'), content_type='text/csv')
        response = self.api_client.post(reverse('project-import-csv'), {'file': uploaded}, format='multipart')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.data['errors']), 0)

    def test_acquire_lock_handles_exceptions(self):
        url = reverse('project-acquire-lock', kwargs={'pk': self.project.id})
        with patch('projects.views.ProjectEditLock.objects.create', side_effect=Exception('fail')):
            response = self.api_client.post(url, {}, format='json')
        self.assertEqual(response.status_code, 500)

    def test_acquire_lock_existing_user_and_conflict(self):
        url = reverse('project-acquire-lock', kwargs={'pk': self.project.id})
        first = self.api_client.post(url, {}, format='json')
        self.assertTrue(first.data['success'])
        second = self.api_client.post(url, {}, format='json')
        self.assertTrue(second.data['success'])
        other_user = User.objects.create_user(email='locker@example.com', password='password123', username='locker@example.com', name='他ユーザー')
        existing_lock = ProjectEditLock.objects.get(project=self.project)
        existing_lock.user = other_user
        existing_lock.expires_at = timezone.now() + timedelta(minutes=30)
        existing_lock.save(update_fields=['user', 'expires_at'])
        conflict = self.api_client.post(url, {}, format='json')
        self.assertEqual(conflict.status_code, 409)

    def test_project_company_viewset_update_and_destroy(self):
        detail_url = reverse('project_company_detail', kwargs={'project_id': self.project.id, 'company_id': self.company.id})
        response = self.api_client.patch(detail_url, {'status': 'DM送信済み'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'DM送信済み')

        response = self.api_client.delete(detail_url)
        self.assertEqual(response.status_code, 204)

    def test_create_snapshot_refresh_false_and_apply_snapshot(self):
        request = self.factory.get('/api/v1/projects/')
        request.user = self.user
        view = ProjectViewSet()
        view.request = request

        snapshot = view._create_snapshot(self.project, self.user, source='test', reason='manual', refresh=False)
        self.assertIsNotNone(snapshot.id)
        snapshot.data = {
            'project': {'appointment_count': 5},
            'project_companies': [
                {
                    'id': None,
                    'company_id': self.company.id,
                    'status': 'DM送信済み',
                }
            ],
        }
        snapshot.save(update_fields=['data'])

        view._apply_snapshot(self.project, snapshot, self.user)
        self.project.refresh_from_db()
        self.assertEqual(self.project.appointment_count, 5)
        self.assertEqual(ProjectCompany.objects.get(pk=self.project_company.pk).status, 'DM送信済み')

    def test_apply_snapshot_skips_missing_company(self):
        request = self.factory.get('/api/v1/projects/')
        request.user = self.user
        view = ProjectViewSet()
        view.request = request
        snapshot = ProjectSnapshot.objects.create(
            project=self.project,
            data={'project': {}, 'project_companies': [{'id': 9999, 'company_id': 9999, 'status': '未接触'}]},
            created_by=self.user,
            source='test'
        )
        view._apply_snapshot(self.project, snapshot, self.user)

    def test_release_lock_branches(self):
        ProjectEditLock.objects.create(project=self.project, user=self.user)
        release_url = reverse('project-release-lock', kwargs={'pk': self.project.id})
        success_response = self.api_client.delete(release_url)
        self.assertTrue(success_response.data['success'])

        other_user = User.objects.create_user(email='release@example.com', password='password123', username='release@example.com', name='解除不可ユーザー')
        ProjectEditLock.objects.create(project=self.project, user=other_user)
        forbidden_response = self.api_client.delete(release_url)
        self.assertEqual(forbidden_response.status_code, 403)
        ProjectEditLock.objects.filter(project=self.project).delete()
        final_response = self.api_client.delete(release_url)
        self.assertTrue(final_response.data['success'])

    def test_perform_partial_update_with_lock_checks(self):
        url = reverse('project-detail', kwargs={'pk': self.project.id})
        other_user = User.objects.create_user(email='locktester@example.com', password='password123', username='locktester@example.com', name='ロッカー')
        ProjectEditLock.objects.create(project=self.project, user=other_user)
        response_conflict = self.api_client.patch(url, {'situation': '衝突'}, format='json')
        self.assertEqual(response_conflict.status_code, 403)
        self.assertFalse(response_conflict.data['success'])
        self.assertIn('ロッカー', response_conflict.data['error'])
        ProjectEditLock.objects.filter(project=self.project).delete()
        response = self.api_client.patch(url, {'situation': '更新'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('snapshot_id', response.data)

    def test_bulk_update_records_serializer_errors(self):
        url = reverse('project-bulk-update')
        payload = {
            'project_ids': [self.project.id],
            'update_data': {'appointment_count': 'invalid-number'}
        }
        response = self.api_client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('errors', response.data)

    def test_list_snapshots_without_pagination(self):
        snapshot = ProjectSnapshot.objects.create(
            project=self.project,
            data={'project': {'appointment_count': 1}},
            created_by=self.user,
            source='bulk_edit'
        )
        with patch.object(ProjectViewSet, 'paginate_queryset', return_value=None):
            response = self.api_client.get(reverse('project-list-snapshots', kwargs={'pk': self.project.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_date_helpers_cover_branches(self):
        view = ProjectViewSet()
        self.assertEqual(view._serialize_date(date(2024, 1, 1)), '2024-01-01')
        self.assertEqual(view._deserialize_date(date(2024, 1, 1)), date(2024, 1, 1))
        self.assertIsNone(view._deserialize_date('invalid'))

class CleanupProjectSnapshotsCommandTests(TestCase):
    """cleanup_project_snapshots コマンドのテスト"""

    def setUp(self):
        self.client_obj = Client.objects.create(name='スナップショットクライアント')
        self.project = Project.objects.create(client=self.client_obj, name='スナップショット案件')

    def _create_snapshot(self, age_days=0):
        snapshot = ProjectSnapshot.objects.create(
            project=self.project,
            data={'project': {}, 'project_companies': []},
            source='bulk_edit'
        )
        if age_days:
            ProjectSnapshot.objects.filter(pk=snapshot.pk).update(
                created_at=timezone.now() - timedelta(days=age_days)
            )
            snapshot.refresh_from_db()
        return snapshot

    def test_cleanup_removes_old_snapshots(self):
        old_snapshot = self._create_snapshot(age_days=10)
        recent_snapshot = self._create_snapshot(age_days=1)

        call_command('cleanup_project_snapshots', '--days', '7')

        self.assertFalse(ProjectSnapshot.objects.filter(pk=old_snapshot.pk).exists())
        self.assertTrue(ProjectSnapshot.objects.filter(pk=recent_snapshot.pk).exists())

    def test_cleanup_dry_run_does_not_delete(self):
        snapshot = self._create_snapshot(age_days=9)
        out = io.StringIO()

        call_command('cleanup_project_snapshots', '--days', '7', '--dry-run', stdout=out)

        self.assertTrue(ProjectSnapshot.objects.filter(pk=snapshot.pk).exists())
        self.assertIn('[DRY-RUN]', out.getvalue())


class ProfileProjectEndpointsCommandTests(TestCase):
    """profile_project_endpoints コマンドのテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='profile@example.com',
            password='password123',
            username='profile@example.com',
            name='計測ユーザー'
        )
        client_obj = Client.objects.create(name='計測クライアント')
        Project.objects.create(client=client_obj, name='計測案件')

    def test_profile_command_runs(self):
        out = io.StringIO()

        call_command(
            'profile_project_endpoints',
            '--user-id', str(self.user.id),
            '--iterations', '1',
            stdout=out,
        )

        self.assertIn('計測が完了しました。', out.getvalue())

    def test_profile_command_errors_without_auth(self):
        with self.assertRaises(CommandError):
            call_command('profile_project_endpoints', '--iterations', '1')

    def test_profile_command_validates_iterations(self):
        with self.assertRaises(CommandError):
            call_command('profile_project_endpoints', '--user-id', str(self.user.id), '--iterations', '0')
