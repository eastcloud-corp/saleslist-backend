#!/usr/bin/env python3
"""
企業管理画面の全フィールド保存テスト
"""

import requests
import json
import sys
from datetime import datetime

class CompanyFieldSaveTest:
    def __init__(self, base_url="http://localhost:8006/api/v1"):
        self.base_url = base_url
        self.admin_token = None
        self.company_id = None
        self.original_data = {}
        
    def authenticate(self) -> bool:
        """認証"""
        try:
            response = requests.post(f"{self.base_url}/auth/login/", json={
                "email": "admin@test.com",
                "password": "password123"
            })
            
            if response.status_code == 200:
                self.admin_token = response.json()['access_token']
                print("✅ 認証成功")
                return True
            else:
                print(f"❌ 認証失敗: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 認証エラー: {e}")
            return False
    
    def get_test_company(self) -> bool:
        """テスト用企業取得"""
        try:
            response = requests.get(
                f"{self.base_url}/companies/?limit=1",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['count'] > 0:
                    self.company_id = data['results'][0]['id']
                    self.original_data = data['results'][0].copy()
                    print(f"✅ テスト企業取得: ID={self.company_id}")
                    return True
                else:
                    print("❌ 企業が存在しません")
                    return False
            else:
                print(f"❌ 企業取得失敗: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 企業取得エラー: {e}")
            return False
    
    def test_company_field_save(self, field_name: str, test_value, field_type: str = "text"):
        """企業フィールドの保存テスト"""
        try:
            # データ更新
            update_data = {field_name: test_value}
            update_response = requests.patch(
                f"{self.base_url}/companies/{self.company_id}/",
                headers={
                    "Authorization": f"Bearer {self.admin_token}",
                    "Content-Type": "application/json"
                },
                json=update_data
            )
            
            if update_response.status_code != 200:
                return False, f"更新失敗: {update_response.status_code} - {update_response.text}"
            
            # 保存確認
            verify_response = requests.get(
                f"{self.base_url}/companies/{self.company_id}/",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )
            
            if verify_response.status_code != 200:
                return False, f"確認取得失敗: {verify_response.status_code}"
            
            saved_data = verify_response.json()
            saved_value = saved_data.get(field_name)
            
            # 値の比較
            if field_type == "boolean":
                success = bool(saved_value) == bool(test_value)
            elif field_type == "integer":
                success = int(saved_value or 0) == int(test_value or 0)
            else:  # text
                success = str(saved_value or "") == str(test_value or "")
            
            return success, saved_value
            
        except Exception as e:
            return False, f"例外: {e}"
    
    def run_all_tests(self):
        """全企業フィールドのテスト実行"""
        print("🧪 企業管理フィールド保存テスト開始")
        print("="*50)
        
        # 企業管理のテスト項目
        test_fields = [
            ("name", "自動テスト企業名", "text"),
            ("industry", "自動テスト業界", "text"),
            ("employee_count", 999, "integer"),
            ("revenue", 1000000000, "integer"),
            ("prefecture", "東京都", "text"),
            ("city", "自動テスト市", "text"),
            ("established_year", 2020, "integer"),
            ("website_url", "https://auto-test.com", "text"),
            ("contact_email", "test@auto-test.com", "text"),
            ("phone", "03-1234-5678", "text"),
            ("notes", "自動テスト備考", "text"),
            ("business_description", "自動テスト事業内容", "text"),
            ("contact_person_name", "自動テスト担当者", "text"),
            ("contact_person_position", "自動テスト役職", "text"),
            ("facebook_url", "https://facebook.com/autotest", "text"),
            ("tob_toc_type", "toB", "text"),
        ]
        
        passed_tests = 0
        failed_tests = 0
        
        for field_name, test_value, field_type in test_fields:
            original_value = self.original_data.get(field_name)
            
            success, result = self.test_company_field_save(field_name, test_value, field_type)
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {field_name}: {'保存成功' if success else f'保存失敗: {result}'}")
            
            if not success and original_value is not None:
                print(f"    Original: {original_value}")
                print(f"    Test Value: {test_value}")
                print(f"    Result: {result}")
            
            if success:
                passed_tests += 1
            else:
                failed_tests += 1
        
        total_tests = passed_tests + failed_tests
        success_rate = round((passed_tests / total_tests) * 100) if total_tests > 0 else 0
        
        print("\n" + "="*50)
        print("📊 企業管理テスト結果サマリー")
        print("="*50)
        print(f"総テスト数: {total_tests}")
        print(f"成功: {passed_tests}")
        print(f"失敗: {failed_tests}")
        print(f"成功率: {success_rate}%")
        
        return success_rate >= 95

def main():
    tester = CompanyFieldSaveTest()
    
    print("🚀 企業管理フィールド保存テストスイート")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 認証
    if not tester.authenticate():
        sys.exit(1)
    
    # テスト用企業取得
    if not tester.get_test_company():
        sys.exit(1)
    
    # 全フィールドテスト実行
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 企業管理フィールドの保存テストが成功しました！")
        sys.exit(0)
    else:
        print("\n💥 企業管理フィールドの保存テストが失敗しました")
        sys.exit(1)

if __name__ == "__main__":
    main()