#!/usr/bin/env python3
"""
フロントエンドデータ表示問題デバッグ
"""

import requests

# 認証
auth = requests.post("http://localhost:8006/api/v1/auth/login/", json={
    "email": "admin@test.com", "password": "password123"
})
token = auth.json()['access_token']

print("🔍 フロントエンドデータ表示問題デバッグ")
print("="*50)

# フロントエンドが呼んでいるであろうAPIエンドポイントを確認
endpoints_to_test = [
    ("/projects/?management_mode=true&page=1&limit=20", "一覧画面用API"),
    ("/projects/6/?management_mode=true", "詳細画面用API"),
    ("/projects/6/", "詳細画面用API（管理モードなし）"),
    ("/projects/?page=1&limit=20", "一覧画面用API（管理モードなし）")
]

for endpoint, description in endpoints_to_test:
    print(f"\n📡 {description}: {endpoint}")
    response = requests.get(
        f"http://localhost:8006/api/v1{endpoint}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        
        if 'results' in data:
            # 一覧形式
            project = next((p for p in data['results'] if p.get('id') == 6), None)
        else:
            # 詳細形式
            project = data if data.get('id') == 6 else None
        
        if project:
            print(f"  案件名: {project.get('name', 'MISSING')}")
            print(f"  アポ数: {project.get('appointment_count', 'MISSING')}")
            print(f"  承認数: {project.get('approval_count', 'MISSING')}")
            print(f"  返信数: {project.get('reply_count', 'MISSING')}")
            print(f"  友達数: {project.get('friends_count', 'MISSING')}")
            print(f"  企業数: {project.get('company_count', 'MISSING')}")
            print(f"  状況: {project.get('situation', 'MISSING')}")
            print(f"  ディレクター: {project.get('director', 'MISSING')}")
        else:
            print("  ❌ プロジェクトID 6が見つかりません")
    else:
        print(f"  ❌ API失敗: {response.status_code}")

print(f"\n🔍 フロントエンドが使用しているAPIの確認:")
print(f"ブラウザのNetworkタブで以下を確認してください:")
print(f"1. プロジェクト一覧: /projects/ のクエリパラメータ")
print(f"2. プロジェクト詳細: /projects/6/ のクエリパラメータ") 
print(f"3. management_mode=true が付いているか")
print(f"4. レスポンスデータの内容")

# 現在のuseProjects hookが正しくmanagement_modeを付けているか確認
print(f"\n💡 チェックポイント:")
print(f"1. useProjects hookでmanagement_mode=trueパラメータが追加されているか")
print(f"2. useProject hookでmanagement_mode=trueパラメータが追加されているか")
print(f"3. フロントエンドでapiClient.handleResponse()が正しく動作しているか")
print(f"4. React stateの更新が正しく反映されているか")