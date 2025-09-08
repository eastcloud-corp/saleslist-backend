#!/usr/bin/env python3
"""
APIレスポンス調査ツール
案件一覧のデータが0・未設定になっている問題を調査
"""

import requests
import json

# 認証
auth_response = requests.post("http://localhost:8006/api/v1/auth/login/", json={
    "email": "admin@test.com",
    "password": "password123"
})

if auth_response.status_code != 200:
    print(f"❌ 認証失敗: {auth_response.status_code}")
    exit(1)

token = auth_response.json()['access_token']
print("✅ 認証成功")

# 管理モードでプロジェクト一覧取得
projects_response = requests.get(
    "http://localhost:8006/api/v1/projects/?management_mode=true",
    headers={"Authorization": f"Bearer {token}"}
)

if projects_response.status_code != 200:
    print(f"❌ プロジェクト取得失敗: {projects_response.status_code}")
    print(projects_response.text)
    exit(1)

data = projects_response.json()
print(f"✅ プロジェクト取得成功: {data['count']}件")

if data['count'] > 0:
    project = data['results'][0]
    print(f"\n🔍 プロジェクトID {project['id']} の詳細:")
    
    # 重要フィールドの値を確認
    fields_to_check = [
        'name', 'client_name', 'appointment_count', 'approval_count', 
        'reply_count', 'friends_count', 'situation', 'progress_status',
        'director', 'operator', 'sales_person', 'progress_tasks',
        'daily_tasks', 'reply_check_notes', 'remarks'
    ]
    
    for field in fields_to_check:
        value = project.get(field, 'FIELD_NOT_FOUND')
        print(f"  {field}: {value}")
    
    print(f"\n📄 完全なプロジェクトデータ:")
    print(json.dumps(project, indent=2, ensure_ascii=False))
else:
    print("❌ プロジェクトデータが存在しません")