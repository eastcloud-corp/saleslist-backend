#!/usr/bin/env python3
"""
NGテスト環境修正
クライアントNG企業のテスト環境を正しく設定
"""

import requests

# 認証
auth = requests.post("http://localhost:8006/api/v1/auth/login/", json={"email": "admin@test.com", "password": "password123"})
token = auth.json()['access_token']

print("🔧 NGテスト環境修正開始")

# 1. 企業ID 2が案件6に追加済みか確認
project_companies = requests.get("http://localhost:8006/api/v1/projects/6/companies/", 
                                headers={"Authorization": f"Bearer {token}"})

added_company_ids = []
if project_companies.status_code == 200:
    for pc in project_companies.json()['results']:
        added_company_ids.append(pc['company_id'])
        print(f"既に追加済み企業: ID{pc['company_id']} {pc['company_name']}")

# 2. 企業ID 2が追加済みなら削除
if 2 in added_company_ids:
    print("\n🗑️  企業ID 2を案件6から削除します...")
    # ProjectCompanyの削除（直接APIがない場合はDjangoシェルで削除）
    delete_response = requests.delete(f"http://localhost:8006/api/v1/projects/6/companies/2/", 
                                    headers={"Authorization": f"Bearer {token}"})
    print(f"削除結果: HTTP {delete_response.status_code}")
    
    if delete_response.status_code != 200:
        print("⚠️  API経由での削除失敗。Django管理画面またはシェルで手動削除が必要")

# 3. 利用可能企業リスト再確認
print("\n🔍 修正後の利用可能企業リスト:")
available = requests.get("http://localhost:8006/api/v1/projects/6/available-companies/", 
                        headers={"Authorization": f"Bearer {token}"})

if available.status_code == 200:
    data = available.json()
    for company in data['results']:
        ng = company.get('ng_status', {})
        status = "🚫NG" if ng.get('is_ng') else "✅OK"
        print(f"  {status} ID{company['id']}: {company['name']}")
        
        if ng.get('is_ng'):
            types = ng.get('types', [])
            print(f"      NG種類: {types}")

# 4. 企業ID 2のクライアントNG設定確認
print("\n🚫 企業ID 2のクライアントNG設定確認:")
client_ng = requests.get("http://localhost:8006/api/v1/clients/1/ng-companies/", 
                        headers={"Authorization": f"Bearer {token}"})

if client_ng.status_code == 200:
    for ng in client_ng.json().get('results', []):
        if ng.get('company_id') == 2 or ng.get('company_name') == '自動テスト企業名':
            print(f"  企業名: {ng.get('company_name')}")
            print(f"  企業ID: {ng.get('company_id')}")
            print(f"  マッチ状態: {ng.get('matched')}")
            print(f"  理由: {ng.get('reason')}")

print("\n✅ NGテスト環境確認完了")