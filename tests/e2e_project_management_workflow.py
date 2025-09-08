"""
プロジェクト管理機能 E2Eワークフローテスト
実際のユーザー操作シナリオをテスト
"""

import time
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from masters.models import ProjectProgressStatus, MediaType
from clients.models import Client
from projects.models import Project, ProjectEditLock
from accounts.models import User


class E2EProjectManagementWorkflowTest(TransactionTestCase):
    """E2E プロジェクト管理ワークフローテスト"""
    
    def setUp(self):
        """テスト環境セットアップ"""
        # ユーザー作成
        self.user_manager = User.objects.create_user(
            email='manager@test.com',
            name='マネージャー',
            password='testpass123'
        )
        self.user_operator = User.objects.create_user(
            email='operator@test.com', 
            name='オペレーター',
            password='testpass123'
        )
        
        # クライアント作成
        self.client_obj = Client.objects.create(name='重要クライアント')
        
        # マスターデータ作成
        self.status_planning = ProjectProgressStatus.objects.create(
            name='未着手', display_order=0
        )
        self.status_operation = ProjectProgressStatus.objects.create(
            name='運用中', display_order=1
        )
        self.status_stopped = ProjectProgressStatus.objects.create(
            name='停止', display_order=2
        )
        
        self.media_facebook = MediaType.objects.create(
            name='Facebook', display_order=0
        )
        
        # プロジェクト作成
        self.project = Project.objects.create(
            client=self.client_obj,
            name='重要案件',
            progress_status=self.status_planning,
            media_type=self.media_facebook,
            appointment_count=0,
            approval_count=0,
            reply_count=0,
            friends_count=0
        )
        
        # APIクライアント
        self.api_manager = APIClient()
        self.api_operator = APIClient()
    
    def _get_auth_token(self, user):
        """認証トークン取得"""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def test_complete_project_management_workflow(self):
        """完全なプロジェクト管理ワークフロー"""
        
        # === シナリオ1: マネージャーが案件を編集開始 ===
        print("\n=== シナリオ1: マネージャーによる編集開始 ===")
        
        manager_token = self._get_auth_token(self.user_manager)
        self.api_manager.credentials(HTTP_AUTHORIZATION=f'Bearer {manager_token}')
        
        # 1-1. 一覧取得
        list_response = self.api_manager.get('/api/v1/projects/?management_mode=true')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertFalse(list_response.data['results'][0]['is_locked'])
        
        # 1-2. 編集ロック取得
        lock_response = self.api_manager.post(f'/api/v1/projects/{self.project.id}/lock/')
        self.assertEqual(lock_response.status_code, status.HTTP_200_OK)
        self.assertTrue(lock_response.data['success'])
        
        # 1-3. プロジェクト更新（マネージャーが進行状況を「運用中」に変更）
        update_response = self.api_manager.patch(
            f'/api/v1/projects/{self.project.id}/?management_mode=true',
            {
                'progress_status_id': self.status_operation.id,
                'director_login_available': True,
                'appointment_count': 5
            }
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # === シナリオ2: 同時に別ユーザーがアクセス（排他制御確認） ===
        print("\n=== シナリオ2: オペレーターによる同時アクセス（排他制御） ===")
        
        operator_token = self._get_auth_token(self.user_operator)
        self.api_operator.credentials(HTTP_AUTHORIZATION=f'Bearer {operator_token}')
        
        # 2-1. オペレーターが一覧取得（ロック状態確認）
        operator_list = self.api_operator.get('/api/v1/projects/?management_mode=true')
        self.assertEqual(operator_list.status_code, status.HTTP_200_OK)
        self.assertTrue(operator_list.data['results'][0]['is_locked'])
        self.assertEqual(operator_list.data['results'][0]['locked_by_name'], 'マネージャー')
        
        # 2-2. オペレーターがロック取得試行（失敗するはず）
        operator_lock = self.api_operator.post(f'/api/v1/projects/{self.project.id}/lock/')
        self.assertEqual(operator_lock.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(operator_lock.data['success'])
        self.assertIn('マネージャー', operator_lock.data['error'])
        
        # === シナリオ3: マネージャーが作業完了・ロック解除 ===
        print("\n=== シナリオ3: マネージャーによる作業完了・ロック解除 ===")
        
        # 3-1. 最終的な数値更新
        final_update = self.api_manager.patch(
            f'/api/v1/projects/{self.project.id}/?management_mode=true',
            {
                'appointment_count': 10,
                'approval_count': 7,
                'reply_count': 15,
                'friends_count': 25,
                'situation': 'マネージャーが更新完了'
            }
        )
        self.assertEqual(final_update.status_code, status.HTTP_200_OK)
        
        # 3-2. ロック解除
        unlock_response = self.api_manager.delete(f'/api/v1/projects/{self.project.id}/lock/')
        self.assertEqual(unlock_response.status_code, status.HTTP_200_OK)
        self.assertTrue(unlock_response.data['success'])
        
        # === シナリオ4: オペレーターが引き継ぎ編集 ===
        print("\n=== シナリオ4: オペレーターによる引き継ぎ編集 ===")
        
        # 4-1. オペレーターがロック取得（今度は成功するはず）
        operator_lock2 = self.api_operator.post(f'/api/v1/projects/{self.project.id}/lock/')
        self.assertEqual(operator_lock2.status_code, status.HTTP_200_OK)
        self.assertTrue(operator_lock2.data['success'])
        
        # 4-2. オペレーターが追加作業
        operator_update = self.api_operator.patch(
            f'/api/v1/projects/{self.project.id}/?management_mode=true',
            {
                'operator_group_invited': True,
                'reply_count': 20,
                'situation': 'オペレーターが引き継ぎ完了'
            }
        )
        self.assertEqual(operator_update.status_code, status.HTTP_200_OK)
        
        # 4-3. 最終状態確認
        final_list = self.api_operator.get('/api/v1/projects/?management_mode=true')
        final_project = final_list.data['results'][0]
        
        self.assertEqual(final_project['appointment_count'], 10)
        self.assertEqual(final_project['approval_count'], 7)
        self.assertEqual(final_project['reply_count'], 20)
        self.assertEqual(final_project['friends_count'], 25)
        self.assertTrue(final_project['director_login_available'])
        self.assertTrue(final_project['operator_group_invited'])
        self.assertEqual(final_project['situation'], 'オペレーターが引き継ぎ完了')
        
        print("✅ 完全なワークフロー成功")
        
    def test_lock_timeout_scenario(self):
        """ロックタイムアウトシナリオテスト"""
        
        print("\n=== ロックタイムアウトシナリオテスト ===")
        
        manager_token = self._get_auth_token(self.user_manager)
        self.api_manager.credentials(HTTP_AUTHORIZATION=f'Bearer {manager_token}')
        
        # ロック取得
        lock_response = self.api_manager.post(f'/api/v1/projects/{self.project.id}/lock/')
        self.assertTrue(lock_response.data['success'])
        
        # 期限切れロックを手動作成（テスト用）
        lock = ProjectEditLock.objects.get(project=self.project)
        lock.expires_at = timezone.now() - timedelta(minutes=1)
        lock.save()
        
        # 別ユーザーがアクセス（期限切れロックは自動削除されるはず）
        operator_token = self._get_auth_token(self.user_operator)
        self.api_operator.credentials(HTTP_AUTHORIZATION=f'Bearer {operator_token}')
        
        operator_lock = self.api_operator.post(f'/api/v1/projects/{self.project.id}/lock/')
        self.assertEqual(operator_lock.status_code, status.HTTP_200_OK)
        self.assertTrue(operator_lock.data['success'])
        
        print("✅ ロックタイムアウト処理成功")

    def test_error_recovery_scenario(self):
        """エラー回復シナリオテスト"""
        
        print("\n=== エラー回復シナリオテスト ===")
        
        manager_token = self._get_auth_token(self.user_manager)
        self.api_manager.credentials(HTTP_AUTHORIZATION=f'Bearer {manager_token}')
        
        # 1. 正常なロック取得
        lock_response = self.api_manager.post(f'/api/v1/projects/{self.project.id}/lock/')
        self.assertTrue(lock_response.data['success'])
        
        # 2. 不正なデータで更新試行
        invalid_update = self.api_manager.patch(
            f'/api/v1/projects/{self.project.id}/?management_mode=true',
            {
                'appointment_count': 'invalid_string',  # 無効なデータ型
                'progress_status_id': 99999  # 存在しないID
            }
        )
        # エラーが発生してもロックは維持される
        
        # 3. ロック状態確認（まだロック中のはず）
        list_response = self.api_manager.get('/api/v1/projects/?management_mode=true')
        self.assertTrue(list_response.data['results'][0]['is_locked'])
        
        # 4. 正しいデータで再試行
        valid_update = self.api_manager.patch(
            f'/api/v1/projects/{self.project.id}/?management_mode=true',
            {
                'appointment_count': 15,
                'progress_status_id': self.status_operation.id
            }
        )
        self.assertEqual(valid_update.status_code, status.HTTP_200_OK)
        
        # 5. ロック解除
        unlock = self.api_manager.delete(f'/api/v1/projects/{self.project.id}/lock/')
        self.assertTrue(unlock.data['success'])
        
        print("✅ エラー回復処理成功")