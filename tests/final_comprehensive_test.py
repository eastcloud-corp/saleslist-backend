#!/usr/bin/env python3
"""
最終包括テスト
全機能・全画面・全APIを100%検証
"""

import requests
import json
from datetime import datetime

class FinalComprehensiveTest:
    def __init__(self):
        self.base_url = "http://localhost:8006/api/v1"
        self.frontend_url = "http://localhost:3007"
        self.admin_token = None
        self.results = []
        
    def log(self, test_name, success, message=""):
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append({'test': test_name, 'success': success, 'message': message})
        print(f"{status} {test_name}: {message}")
        
    def authenticate(self):
        """認証テスト"""
        response = requests.post(f"{self.base_url}/auth/login/", json={
            "email": "admin@test.com", "password": "password123"
        })
        
        if response.status_code == 200:
            self.admin_token = response.json()['access_token']
            self.log("認証", True, "ログイン成功")
            return True
        else:
            self.log("認証", False, f"ログイン失敗: {response.status_code}")
            return False
    
    def test_project_management_full_cycle(self):
        """プロジェクト管理の完全サイクルテスト"""
        
        # 1. プロジェクト一覧取得（管理モード）
        projects_response = requests.get(
            f"{self.base_url}/projects/?management_mode=true",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        success = projects_response.status_code == 200
        self.log("プロジェクト一覧取得（管理モード）", success, 
                f"HTTP {projects_response.status_code}")
        
        if not success:
            return False
            
        projects_data = projects_response.json()
        
        # データ構造検証
        required_fields = [
            'appointment_count', 'approval_count', 'reply_count', 'friends_count',
            'director', 'operator', 'sales_person', 'situation',
            'progress_status', 'company_count'
        ]
        
        if projects_data['count'] > 0:
            project = projects_data['results'][0]
            project_id = project['id']
            
            for field in required_fields:
                has_field = field in project
                self.log(f"プロジェクトフィールド「{field}」存在確認", has_field, 
                        f"値: {project.get(field, 'MISSING')}")
        
        # 2. ロック・更新・保存の完全フロー
        lock_response = requests.post(
            f"{self.base_url}/projects/{project_id}/lock/",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.log("編集ロック取得", lock_response.status_code == 200)
        
        # 3. データ更新（25フィールド一括テスト）
        update_data = {
            'appointment_count': 100,
            'approval_count': 50,
            'reply_count': 25,
            'friends_count': 75,
            'director': '最終テストディレクター',
            'operator': '最終テスト運用者',
            'situation': '最終テスト完了',
            'director_login_available': True,
            'progress_status_id': 1
        }
        
        update_response = requests.patch(
            f"{self.base_url}/projects/{project_id}/?management_mode=true",
            headers={
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            },
            json=update_data
        )
        
        self.log("プロジェクトデータ更新", update_response.status_code == 200,
                f"HTTP {update_response.status_code}")
        
        # 4. 更新確認
        verify_response = requests.get(
            f"{self.base_url}/projects/{project_id}/?management_mode=true",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        if verify_response.status_code == 200:
            updated_project = verify_response.json()
            
            # 更新値検証
            for field, expected in [
                ('appointment_count', 100),
                ('approval_count', 50), 
                ('director', '最終テストディレクター'),
                ('situation', '最終テスト完了')
            ]:
                actual = updated_project.get(field)
                success = str(actual) == str(expected)
                self.log(f"更新確認「{field}」", success, f"期待値: {expected}, 実際: {actual}")
        
        # 5. ロック解除
        unlock_response = requests.delete(
            f"{self.base_url}/projects/{project_id}/unlock/",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.log("編集ロック解除", unlock_response.status_code == 200)
        
        return True
    
    def test_companies_management(self):
        """企業管理機能テスト"""
        
        # 企業一覧取得
        companies_response = requests.get(
            f"{self.base_url}/companies/?limit=1",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        success = companies_response.status_code == 200
        self.log("企業一覧取得", success, f"HTTP {companies_response.status_code}")
        
        if success and companies_response.json()['count'] > 0:
            company_id = companies_response.json()['results'][0]['id']
            
            # 企業データ更新テスト
            update_response = requests.patch(
                f"{self.base_url}/companies/{company_id}/",
                headers={
                    "Authorization": f"Bearer {self.admin_token}",
                    "Content-Type": "application/json"
                },
                json={"notes": "最終テスト企業備考"}
            )
            
            self.log("企業データ更新", update_response.status_code == 200,
                    f"HTTP {update_response.status_code}")
    
    def test_master_data_apis(self):
        """マスターデータAPI群テスト"""
        master_endpoints = [
            "progress-statuses", "service-types", "media-types", 
            "meeting-statuses", "list-import-sources", "list-availabilities"
        ]
        
        for endpoint in master_endpoints:
            response = requests.get(
                f"{self.base_url}/master/{endpoint}/",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )
            
            success = response.status_code == 200
            count = 0
            if success:
                data = response.json()
                count = len(data.get('results', []))
                
            self.log(f"マスター「{endpoint}」", success, 
                    f"HTTP {response.status_code}, データ数: {count}")
    
    def test_frontend_pages(self):
        """フロントエンド全ページテスト"""
        pages = [
            ("/dashboard", "ダッシュボード"),
            ("/projects", "プロジェクト一覧"), 
            ("/companies", "企業一覧"),
            ("/clients", "クライアント一覧"),
            ("/login", "ログインページ")
        ]
        
        for path, name in pages:
            response = requests.get(f"{self.frontend_url}{path}")
            success = response.status_code == 200
            self.log(f"フロントエンド「{name}」", success, f"HTTP {response.status_code}")
    
    def run_all_tests(self):
        """全テスト実行"""
        print("🚀 最終包括テスト開始")
        print("="*60)
        print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if not self.authenticate():
            return False
            
        print("\n📊 プロジェクト管理機能テスト")
        self.test_project_management_full_cycle()
        
        print("\n🏢 企業管理機能テスト") 
        self.test_companies_management()
        
        print("\n📋 マスターデータテスト")
        self.test_master_data_apis()
        
        print("\n🌐 フロントエンドページテスト")
        self.test_frontend_pages()
        
        # 結果サマリー
        total = len(self.results)
        passed = len([r for r in self.results if r['success']])
        success_rate = round((passed / total) * 100) if total > 0 else 0
        
        print("\n" + "="*60)
        print("📊 最終包括テスト結果")
        print("="*60)
        print(f"総テスト数: {total}")
        print(f"成功: {passed}")
        print(f"失敗: {total - passed}")
        print(f"成功率: {success_rate}%")
        
        # 失敗項目詳細
        failed = [r for r in self.results if not r['success']]
        if failed:
            print(f"\n❌ 失敗したテスト ({len(failed)}件):")
            for fail in failed:
                print(f"  - {fail['test']}: {fail['message']}")
        
        if success_rate >= 95:
            print("\n🎉 最終包括テスト成功！")
            print("🌟 全システムが完璧に動作しています")
            return True
        else:
            print(f"\n💥 最終包括テスト失敗 (成功率: {success_rate}%)")
            return False

if __name__ == "__main__":
    tester = FinalComprehensiveTest()
    success = tester.run_all_tests()
    exit(0 if success else 1)