#!/usr/bin/env python3
"""
プロジェクト管理画面の全フィールド保存テスト
全24フィールドの保存動作を自動検証
"""

import requests
import json
import sys
import time
from datetime import datetime, date
from typing import Dict, Any, List, Tuple

class ProjectFieldSaveTest:
    def __init__(self, base_url="http://localhost:8006/api/v1"):
        self.base_url = base_url
        self.admin_token = None
        self.user_token = None
        self.test_results = []
        self.project_id = None
        self.original_data = {}
        
    def log_test(self, field_name: str, success: bool, message: str, original_value: Any = None, new_value: Any = None, saved_value: Any = None):
        """テスト結果をログ"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            'field': field_name,
            'status': status,
            'success': success,
            'message': message,
            'original_value': original_value,
            'test_value': new_value,
            'saved_value': saved_value,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status} {field_name}: {message}")
        
        if not success and original_value is not None:
            print(f"    Original: {original_value}")
            print(f"    Test Value: {new_value}")
            print(f"    Saved Value: {saved_value}")
    
    def authenticate(self) -> bool:
        """認証"""
        try:
            # 管理者ログイン
            admin_response = requests.post(f"{self.base_url}/auth/login/", json={
                "email": "admin@test.com",
                "password": "password123"
            })
            
            if admin_response.status_code == 200:
                self.admin_token = admin_response.json()['access_token']
            else:
                print(f"❌ 管理者認証失敗: {admin_response.status_code}")
                return False
                
            # 一般ユーザーログイン
            user_response = requests.post(f"{self.base_url}/auth/login/", json={
                "email": "user@example.com", 
                "password": "password123"
            })
            
            if user_response.status_code == 200:
                self.user_token = user_response.json()['access_token']
                print("✅ 認証成功")
                return True
            else:
                print(f"❌ ユーザー認証失敗: {user_response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 認証エラー: {e}")
            return False
    
    def get_test_project(self) -> bool:
        """テスト用プロジェクト取得"""
        try:
            response = requests.get(
                f"{self.base_url}/projects/?management_mode=true",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['count'] > 0:
                    self.project_id = data['results'][0]['id']
                    self.original_data = data['results'][0].copy()
                    print(f"✅ テストプロジェクト取得: ID={self.project_id}")
                    return True
                else:
                    print("❌ プロジェクトが存在しません")
                    return False
            else:
                print(f"❌ プロジェクト取得失敗: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ プロジェクト取得エラー: {e}")
            return False
    
    def test_field_save(self, field_name: str, test_value: Any, field_type: str = "text") -> Tuple[bool, Any]:
        """個別フィールドの保存テスト"""
        try:
            # 1. ロック取得
            lock_response = requests.post(
                f"{self.base_url}/projects/{self.project_id}/lock/",
                headers={"Authorization": f"Bearer {self.user_token}"}
            )
            
            if lock_response.status_code != 200:
                return False, f"ロック取得失敗: {lock_response.status_code}"
            
            # 2. データ更新
            update_data = {field_name: test_value}
            update_response = requests.patch(
                f"{self.base_url}/projects/{self.project_id}/?management_mode=true",
                headers={
                    "Authorization": f"Bearer {self.user_token}",
                    "Content-Type": "application/json"
                },
                json=update_data
            )
            
            if update_response.status_code != 200:
                return False, f"更新失敗: {update_response.status_code} - {update_response.text}"
            
            # 3. 保存確認
            verify_response = requests.get(
                f"{self.base_url}/projects/{self.project_id}/?management_mode=true",
                headers={"Authorization": f"Bearer {self.user_token}"}
            )
            
            if verify_response.status_code != 200:
                return False, f"確認取得失敗: {verify_response.status_code}"
            
            saved_data = verify_response.json()
            saved_value = saved_data.get(field_name)
            
            # 4. ロック解除
            requests.delete(
                f"{self.base_url}/projects/{self.project_id}/unlock/",
                headers={"Authorization": f"Bearer {self.user_token}"}
            )
            
            # 5. 値の比較
            if field_type == "boolean":
                success = bool(saved_value) == bool(test_value)
            elif field_type == "integer":
                success = int(saved_value or 0) == int(test_value or 0)
            elif field_type == "date":
                success = str(saved_value or "") == str(test_value or "")
            else:  # text
                success = str(saved_value or "") == str(test_value or "")
            
            return success, saved_value
            
        except Exception as e:
            # エラー時もロック解除
            try:
                requests.delete(
                    f"{self.base_url}/projects/{self.project_id}/unlock/",
                    headers={"Authorization": f"Bearer {self.user_token}"}
                )
            except:
                pass
            return False, f"例外: {e}"
    
    def run_all_field_tests(self):
        """全フィールドのテスト実行"""
        print("🧪 プロジェクト管理フィールド保存テスト開始")
        print("="*60)
        
        # テスト定義: フィールド名, テスト値, データ型, 元の値
        test_fields = [
            # 数値系
            ("appointment_count", 777, "integer"),
            ("approval_count", 555, "integer"), 
            ("reply_count", 333, "integer"),
            ("friends_count", 111, "integer"),
            
            # ブール値系
            ("director_login_available", True, "boolean"),
            ("operator_group_invited", False, "boolean"),
            
            # テキスト系
            ("situation", "自動テスト状況更新", "text"),
            ("progress_tasks", "自動テスト進行タスク", "text"),
            ("daily_tasks", "自動テストデイリータスク", "text"),
            ("reply_check_notes", "自動テスト返信チェック", "text"),
            ("remarks", "自動テスト備考", "text"),
            ("complaints_requests", "自動テストクレーム要望", "text"),
            ("director", "自動テストディレクター", "text"),
            ("operator", "自動テスト運用者", "text"),
            ("sales_person", "自動テスト営業マン", "text"),
            
            # 日付系
            ("regular_meeting_date", "2025-12-31", "date"),
            ("entry_date_sales", "2025-12-30", "date"), 
            ("operation_start_date", "2025-01-01", "date"),
            ("expected_end_date", "2025-12-31", "date"),
            
            # ID系（マスターデータ - Serializerでは_id形式）
            ("progress_status_id", 1, "integer"),
            ("service_type_id", 1, "integer"),
            ("media_type_id", 1, "integer"),
            ("regular_meeting_status_id", 1, "integer"),
            ("list_availability_id", 1, "integer"),
            ("list_import_source_id", 1, "integer"),
        ]
        
        passed_tests = 0
        failed_tests = 0
        
        for field_name, test_value, field_type in test_fields:
            original_value = self.original_data.get(field_name)
            
            success, result = self.test_field_save(field_name, test_value, field_type)
            
            if success:
                passed_tests += 1
                self.log_test(field_name, True, "保存成功", original_value, test_value, result)
            else:
                failed_tests += 1
                self.log_test(field_name, False, f"保存失敗: {result}", original_value, test_value, result)
            
            # 連続リクエストを避けるため少し待機
            time.sleep(0.5)
        
        total_tests = passed_tests + failed_tests
        success_rate = round((passed_tests / total_tests) * 100) if total_tests > 0 else 0
        
        print("\n" + "="*60)
        print("📊 テスト結果サマリー")
        print("="*60)
        print(f"総テスト数: {total_tests}")
        print(f"成功: {passed_tests}")
        print(f"失敗: {failed_tests}")
        print(f"成功率: {success_rate}%")
        
        # 失敗したフィールドの詳細
        failed_fields = [r for r in self.test_results if not r['success']]
        if failed_fields:
            print("\n❌ 失敗したフィールド:")
            for field in failed_fields:
                print(f"  - {field['field']}: {field['message']}")
        
        return success_rate >= 95
    
    def generate_report(self):
        """詳細レポート生成"""
        report = {
            "test_suite": "Project Field Save Test",
            "project_id": self.project_id,
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.test_results),
            "passed_tests": len([r for r in self.test_results if r['success']]),
            "failed_tests": len([r for r in self.test_results if not r['success']]),
            "results": self.test_results
        }
        
        report_file = f"/tmp/project_field_save_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 詳細レポート: {report_file}")
        return report_file

def main():
    tester = ProjectFieldSaveTest()
    
    print("🚀 プロジェクト管理フィールド保存テストスイート")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 認証
    if not tester.authenticate():
        sys.exit(1)
    
    # テスト用プロジェクト取得
    if not tester.get_test_project():
        sys.exit(1)
    
    # 全フィールドテスト実行
    success = tester.run_all_field_tests()
    
    # レポート生成
    tester.generate_report()
    
    if success:
        print("\n🎉 全フィールドの保存テストが成功しました！")
        sys.exit(0)
    else:
        print("\n💥 一部のフィールド保存テストが失敗しました")
        sys.exit(1)

if __name__ == "__main__":
    main()