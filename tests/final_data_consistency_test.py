#!/usr/bin/env python3
"""
最終データ整合性テスト
フロントエンドで表示される数字が正しいかの最終確認
"""

import requests

# 認証
auth = requests.post("http://localhost:8006/api/v1/auth/login/", json={
    "email": "admin@test.com", "password": "password123"
})
token = auth.json()['access_token']

print("🎯 最終データ整合性テスト")
print("="*40)

# フロントエンドが現在呼んでいるAPIを確認
print("✅ フロントエンドの修正後APIレスポンス確認:")

# 1. 一覧画面
list_response = requests.get(
    "http://localhost:8006/api/v1/projects/?management_mode=true&page=1&limit=20",
    headers={"Authorization": f"Bearer {token}"}
)

if list_response.status_code == 200:
    list_data = list_response.json()
    project = next((p for p in list_data['results'] if p['id'] == 6), None)
    
    print("\n📋 一覧画面（修正後）:")
    if project:
        print(f"  アポ数: {project.get('appointment_count')} ← これが一覧画面に表示されるべき")
        print(f"  承認数: {project.get('approval_count')}")
        print(f"  返信数: {project.get('reply_count')}")
        print(f"  友達数: {project.get('friends_count')}")
        print(f"  企業数: {project.get('company_count')}")

# 2. 詳細画面
detail_response = requests.get(
    "http://localhost:8006/api/v1/projects/6/?management_mode=true",
    headers={"Authorization": f"Bearer {token}"}
)

if detail_response.status_code == 200:
    detail_project = detail_response.json()
    
    print("\n🔍 詳細画面（修正後）:")
    print(f"  アポ数: {detail_project.get('appointment_count')} ← これが詳細画面に表示されるべき")
    print(f"  承認数: {detail_project.get('approval_count')}")
    print(f"  返信数: {detail_project.get('reply_count')}")
    print(f"  友達数: {detail_project.get('friends_count')}")
    print(f"  企業数: {detail_project.get('company_count')}")

# 判定
list_appointment = project.get('appointment_count') if 'project' in locals() else None
detail_appointment = detail_project.get('appointment_count') if detail_response.status_code == 200 else None

print(f"\n🎯 最終判定:")
if list_appointment == detail_appointment and list_appointment == 100:
    print("✅ データ一致確認: 一覧と詳細で同じ数字が表示されるはず")
    print("   もしフロントエンドで0が表示されている場合：")
    print("   1. ブラウザキャッシュをクリア")
    print("   2. ページリロード")
    print("   3. React state更新の確認")
else:
    print("❌ まだデータ不一致があります")
    print(f"   一覧アポ数: {list_appointment}")
    print(f"   詳細アポ数: {detail_appointment}")

print(f"\n🔄 次のアクション:")
print("ブラウザでhttp://localhost:3007/projects にアクセスして")
print("コンサルティング案件Eの数字が以下のように表示されることを確認:")
print("  - アポ数: 100")
print("  - 承認数: 50")
print("  - 返信数: 25")
print("  - 友達数: 75")
print("  - 企業数: 1")