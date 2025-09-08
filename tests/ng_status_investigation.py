#!/usr/bin/env python3
"""
NG設定状況調査
クライアントNG、グローバルNG、案件NGの設定状況を詳細調査
"""

import requests
import json

# 認証
auth_response = requests.post("http://localhost:8006/api/v1/auth/login/", json={
    "email": "admin@test.com",
    "password": "password123"
})

token = auth_response.json()['access_token']
print("✅ 認証成功")

print("\n🔍 NG設定状況調査開始")
print("="*60)

# 1. 企業のグローバルNG設定確認
print("1. グローバルNG企業確認")
companies_response = requests.get(
    "http://localhost:8006/api/v1/companies/",
    headers={"Authorization": f"Bearer {token}"}
)

companies_data = companies_response.json()
global_ng_companies = [c for c in companies_data['results'] if c.get('is_global_ng', False)]

print(f"  総企業数: {companies_data['count']}")
print(f"  グローバルNG企業: {len(global_ng_companies)}")

for company in global_ng_companies:
    print(f"    - ID {company['id']}: {company['name']} (グローバルNG)")

# 2. クライアントNG企業確認
print("\n2. クライアントNG企業確認")
clients_response = requests.get(
    "http://localhost:8006/api/v1/clients/",
    headers={"Authorization": f"Bearer {token}"}
)

if clients_response.status_code == 200:
    clients_data = clients_response.json()
    for client in clients_data['results']:
        client_id = client['id']
        print(f"  クライアント {client_id}: {client['name']}")
        
        # クライアント別NG企業リスト取得
        client_ng_response = requests.get(
            f"http://localhost:8006/api/v1/clients/{client_id}/ng-companies/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if client_ng_response.status_code == 200:
            client_ng_data = client_ng_response.json()
            print(f"    NG企業数: {len(client_ng_data.get('results', []))}")
            
            for ng_company in client_ng_data.get('results', []):
                print(f"      - {ng_company.get('company_name', 'unknown')} (理由: {ng_company.get('reason', 'none')})")

# 3. 案件6の利用可能企業とNG判定確認
print("\n3. 案件6の利用可能企業・NG判定確認")
project_companies_response = requests.get(
    "http://localhost:8006/api/v1/projects/6/available-companies/",
    headers={"Authorization": f"Bearer {token}"}
)

if project_companies_response.status_code == 200:
    available_data = project_companies_response.json()
    print(f"  利用可能企業数: {available_data['count']}")
    
    for company in available_data['results']:
        ng_status = company.get('ng_status', {})
        is_ng = ng_status.get('is_ng', False)
        ng_types = ng_status.get('types', [])
        
        print(f"  企業ID {company['id']}: {company['name']}")
        print(f"    - is_global_ng: {company.get('is_global_ng', False)}")
        print(f"    - ng_status.is_ng: {is_ng}")
        print(f"    - ng_status.types: {ng_types}")
        
        if is_ng:
            reasons = ng_status.get('reasons', {})
            print(f"    - 理由: {reasons}")
            print(f"    ➜ ❌ NG企業（選択不可であるべき）")
        else:
            print(f"    ➜ ✅ 正常企業（選択可能）")

# 4. 企業名でNG判定の一致確認
print("\n4. 企業名一致によるNG判定確認")
print("  自動テスト企業名 vs v0レポート解決確認企業")

# "自動テスト企業名"がクライアントNGリストにあって、"v0レポート解決確認企業"がグローバルNGの状況を確認
test_companies = ["自動テスト企業名", "v0レポート解決確認企業"]

for company_name in test_companies:
    company_search = requests.get(
        f"http://localhost:8006/api/v1/companies/?search={company_name}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if company_search.status_code == 200:
        search_data = company_search.json()
        if search_data['count'] > 0:
            company = search_data['results'][0]
            print(f"  {company_name}:")
            print(f"    - ID: {company['id']}")
            print(f"    - is_global_ng: {company.get('is_global_ng', False)}")
            print(f"    - 実際の企業名: {company['name']}")
        else:
            print(f"  {company_name}: 企業が見つかりません")

print("\n📝 結論:")
print("NGリストに「自動テスト企業名」があるが、実際の企業は「v0レポート解決確認企業」")
print("企業名の不一致により、NG判定が正しく働いていない可能性があります")