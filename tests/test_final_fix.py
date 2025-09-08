#!/usr/bin/env python3
"""
最終修正テスト
全ての修正が適用された状態での動作確認
"""

import requests
import time

def test_all_functionality():
    # 認証
    auth = requests.post("http://localhost:8006/api/v1/auth/login/", json={
        "email": "admin@test.com", "password": "password123"
    })
    token = auth.json()['access_token']
    
    print("🧪 最終修正テスト開始")
    print("="*40)
    
    tests = []
    
    # 1. プロジェクト一覧（管理モード）
    list_response = requests.get(
        "http://localhost:8006/api/v1/projects/?management_mode=true&page=1&limit=20",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    success = list_response.status_code == 200
    tests.append(("プロジェクト一覧API", success))
    
    if success:
        project = next((p for p in list_response.json()['results'] if p['id'] == 6), None)
        if project:
            has_data = project.get('appointment_count') == 100
            tests.append(("一覧画面データ確認", has_data))
    
    # 2. プロジェクト詳細（管理モード）  
    detail_response = requests.get(
        "http://localhost:8006/api/v1/projects/6/?management_mode=true",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    success = detail_response.status_code == 200
    tests.append(("プロジェクト詳細API", success))
    
    if success:
        detail_project = detail_response.json()
        has_data = detail_project.get('appointment_count') == 100
        tests.append(("詳細画面データ確認", has_data))
    
    # 3. フロントエンドページアクセス
    frontend_response = requests.get("http://localhost:3007/projects")
    tests.append(("フロントエンド一覧ページ", frontend_response.status_code == 200))
    
    detail_frontend_response = requests.get("http://localhost:3007/projects/6")
    tests.append(("フロントエンド詳細ページ", detail_frontend_response.status_code == 200))
    
    # 4. 企業追加API（NG制御確認）
    add_response = requests.post(
        "http://localhost:8006/api/v1/projects/6/add-companies/",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={"company_ids": [1]}  # グローバルNG企業
    )
    
    ng_blocked = add_response.status_code == 200 and add_response.json().get('added_count', 1) == 0
    tests.append(("NG企業追加防止", ng_blocked))
    
    # 結果サマリー
    passed = len([t for t in tests if t[1]])
    total = len(tests)
    success_rate = round((passed / total) * 100)
    
    print("\n📊 テスト結果:")
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n成功率: {passed}/{total} ({success_rate}%)")
    
    if success_rate >= 100:
        print("🎉 全テスト成功！システム完全復旧")
        return True
    else:
        print("⚠️  一部テスト失敗。要追加修正")
        return False

if __name__ == "__main__":
    success = test_all_functionality()
    exit(0 if success else 1)