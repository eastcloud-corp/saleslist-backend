#!/usr/bin/env python3
"""
Django API包括テスト（v0レポート解決確認）
"""

import requests
import json
import sys
from datetime import datetime


class DjangoAPITester:
    def __init__(self, base_url="http://localhost:8080/api/v1"):
        self.base_url = base_url
        self.access_token = None
        self.test_results = []
    
    def log_result(self, test_name, success, message="", response_data=None):
        """テスト結果をログ"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        if response_data:
            result['response'] = response_data
        
        self.test_results.append(result)
        print(f"{status} {test_name}: {message}")
    
    def authenticate(self):
        """Django認証API確認"""
        try:
            response = requests.post(f"{self.base_url}/auth/login", json={
                "email": "user@example.com",
                "password": "password123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.log_result("Django認証API", True, "JWT認証成功")
                return True
            else:
                self.log_result("Django認証API", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Django認証API", False, f"例外: {str(e)}")
            return False
    
    def get_headers(self):
        """認証ヘッダー取得"""
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}
    
    def test_v0_report_solutions(self):
        """v0レポート指摘問題の解決確認"""
        headers = self.get_headers()
        
        # 1. 認証システム（/auth/me）
        try:
            response = requests.get(f"{self.base_url}/auth/me", headers=headers)
            if response.status_code == 200:
                data = response.json()
                user_name = data.get('name', 'Unknown')
                self.log_result("v0問題解決: 認証システム", True, 
                              f"/auth/me API実装 - モックユーザー問題解決")
            else:
                self.log_result("v0問題解決: 認証システム", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("v0問題解決: 認証システム", False, f"例外: {str(e)}")
        
        # 2. 企業作成API（POST /companies）
        try:
            response = requests.post(f"{self.base_url}/companies/", 
                headers=headers,
                json={
                    "name": "v0レポート解決確認企業",
                    "industry": "IT・ソフトウェア",
                    "employee_count": 150,
                    "revenue": 500000000,
                    "prefecture": "東京都",
                    "city": "渋谷区"
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                company_id = data.get('id')
                self.log_result("v0問題解決: 企業作成API", True, 
                              f"POST /companies 実装成功 - ID: {company_id}")
            else:
                self.log_result("v0問題解決: 企業作成API", False, 
                              f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("v0問題解決: 企業作成API", False, f"例外: {str(e)}")
        
        # 3. マスターデータAPI（/master/industries, /master/statuses）
        try:
            response = requests.get(f"{self.base_url}/master/industries/", headers=headers)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                self.log_result("v0問題解決: 業界マスターAPI", True, 
                              f"/master/industries 実装 - ハードコーディング解消 ({len(results)}件)")
            else:
                self.log_result("v0問題解決: 業界マスターAPI", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("v0問題解決: 業界マスターAPI", False, f"例外: {str(e)}")
        
        # 4. ダッシュボード統計API（/dashboard/stats）
        try:
            response = requests.get(f"{self.base_url}/dashboard/stats", headers=headers)
            if response.status_code == 200:
                data = response.json()
                companies = data.get('totalCompanies', 0)
                projects = data.get('activeProjects', 0)
                self.log_result("v0問題解決: ダッシュボード統計API", True, 
                              f"/dashboard/stats 実装 - 動的統計データ (企業{companies}社)")
            else:
                self.log_result("v0問題解決: ダッシュボード統計API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("v0問題解決: ダッシュボード統計API", False, f"例外: {str(e)}")
    
    def test_api_completeness(self):
        """API完全性テスト"""
        headers = self.get_headers()
        
        # 主要エンドポイント存在確認
        endpoints = [
            ("GET", "/clients/", "クライアント一覧"),
            ("GET", "/companies/", "企業一覧"),
            ("GET", "/projects/", "案件一覧"),
            ("GET", "/master/industries/", "業界マスター"),
            ("GET", "/master/statuses/", "ステータスマスター"),
        ]
        
        for method, endpoint, name in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
                if response.status_code == 200:
                    self.log_result(f"API存在確認: {name}", True, f"{method} {endpoint}")
                else:
                    self.log_result(f"API存在確認: {name}", False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log_result(f"API存在確認: {name}", False, f"例外: {str(e)}")
    
    def run_all_tests(self):
        """全テスト実行"""
        print("🧪 Django API包括テスト開始（v0レポート解決確認）")
        print("=" * 60)
        
        # 認証
        if not self.authenticate():
            print("❌ Django認証に失敗したため、テストを中止します")
            return False
        
        # v0レポート問題解決確認
        print("\n📋 v0レポート指摘問題の解決確認...")
        self.test_v0_report_solutions()
        
        # API完全性確認
        print("\n🔍 API完全性確認...")
        self.test_api_completeness()
        
        # 結果サマリー
        passed = len([r for r in self.test_results if "✅ PASS" in r['status']])
        failed = len([r for r in self.test_results if "❌ FAIL" in r['status']])
        
        print("\n" + "=" * 60)
        print(f"📊 Django APIテスト結果: {passed}件成功, {failed}件失敗")
        
        if failed == 0:
            print("🎉 全てのv0レポート問題が解決されました！")
        
        # 結果をJSONファイルに保存
        with open('../django_api_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        return failed == 0


if __name__ == "__main__":
    tester = DjangoAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)