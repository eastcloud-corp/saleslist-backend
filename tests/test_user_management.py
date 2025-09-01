#!/usr/bin/env python3
"""
ユーザー管理API完全テスト
設定画面での新規ユーザー作成・一覧取得機能検証
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8080"

def get_auth_token():
    """認証トークン取得"""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "user@example.com",
        "password": "password123"
    })
    if response.status_code == 200:
        return response.json()['access_token']
    return None

def test_user_apis():
    """ユーザー管理API完全テスト"""
    
    # 認証
    token = get_auth_token()
    if not token:
        print("❌ 認証失敗")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ 認証成功")
    
    test_results = []
    
    # 1. ユーザー一覧取得テスト
    print("\n🔍 ユーザー一覧取得テスト")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/auth/users/", headers=headers)
        if response.status_code == 200:
            data = response.json()
            user_count = data.get('count', 0)
            print(f"   ✅ ユーザー一覧取得成功: {user_count}人")
            test_results.append({"test": "ユーザー一覧", "status": "SUCCESS"})
        else:
            print(f"   ❌ ユーザー一覧取得失敗: {response.status_code}")
            test_results.append({"test": "ユーザー一覧", "status": "FAILED"})
    except Exception as e:
        print(f"   ❌ ユーザー一覧取得エラー: {e}")
        test_results.append({"test": "ユーザー一覧", "status": "ERROR"})
    
    # 2. ユーザー作成テスト
    print("\n🔍 ユーザー作成テスト")
    test_user_data = {
        "name": "テスト太郎",
        "email": "test@example.com", 
        "role": "user",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/users/create/", 
                               headers=headers, 
                               json=test_user_data)
        if response.status_code == 201:
            created_user = response.json()
            print(f"   ✅ ユーザー作成成功: {created_user['name']} ({created_user['email']})")
            test_results.append({"test": "ユーザー作成", "status": "SUCCESS", "user_id": created_user['id']})
        else:
            print(f"   ❌ ユーザー作成失敗: {response.status_code} - {response.text}")
            test_results.append({"test": "ユーザー作成", "status": "FAILED"})
    except Exception as e:
        print(f"   ❌ ユーザー作成エラー: {e}")
        test_results.append({"test": "ユーザー作成", "status": "ERROR"})
    
    # 3. 作成ユーザーの一覧での確認
    print("\n🔍 作成後ユーザー一覧再確認")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/auth/users/", headers=headers)
        if response.status_code == 200:
            data = response.json()
            user_count = data.get('count', 0)
            users = data.get('results', [])
            test_user = next((u for u in users if u['email'] == 'test@example.com'), None)
            
            if test_user:
                print(f"   ✅ 作成ユーザー確認済み: {test_user['name']}")
                test_results.append({"test": "作成ユーザー確認", "status": "SUCCESS"})
            else:
                print(f"   ❌ 作成ユーザーが一覧に表示されない")
                test_results.append({"test": "作成ユーザー確認", "status": "FAILED"})
        else:
            print(f"   ❌ ユーザー一覧再取得失敗: {response.status_code}")
            test_results.append({"test": "作成ユーザー確認", "status": "FAILED"})
    except Exception as e:
        print(f"   ❌ ユーザー一覧再取得エラー: {e}")
        test_results.append({"test": "作成ユーザー確認", "status": "ERROR"})
    
    # 結果サマリー
    print("\n" + "=" * 50)
    success_count = len([r for r in test_results if r['status'] == 'SUCCESS'])
    total_count = len(test_results)
    
    print(f"📊 ユーザー管理APIテスト結果: {success_count}/{total_count} 成功")
    
    if success_count == total_count:
        print("🎉 ユーザー管理機能100%動作確認！")
        return True
    else:
        print(f"⚠️ {total_count - success_count}個のテストが失敗")
        return False

if __name__ == "__main__":
    test_user_apis()