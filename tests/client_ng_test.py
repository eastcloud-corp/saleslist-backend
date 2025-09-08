#!/usr/bin/env python3
"""
クライアントNG機能テスト
クライアント別NG企業が正しく判定されているかテスト
"""

import requests

# 認証
auth_response = requests.post("http://localhost:8006/api/v1/auth/login/", json={
    "email": "admin@test.com",
    "password": "password123"
})

token = auth_response.json()['access_token']
print("✅ 認証成功")

# プロジェクト6の詳細取得（クライアント情報確認）
project_response = requests.get(
    "http://localhost:8006/api/v1/projects/6/?management_mode=true",
    headers={"Authorization": f"Bearer {token}"}
)

if project_response.status_code == 200:
    project_data = project_response.json()
    print(f"📊 プロジェクト6: {project_data['name']}")
    print(f"   クライアント名: {project_data.get('client_name', 'unknown')}")
    
    # クライアントIDを取得する必要がある
    projects_list_response = requests.get(
        "http://localhost:8006/api/v1/projects/6/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if projects_list_response.status_code == 200:
        project_detail = projects_list_response.json()
        client_id = project_detail.get('client')
        print(f"   クライアントID: {client_id}")
        
        if client_id:
            # クライアントのNG企業リスト確認
            client_ng_response = requests.get(
                f"http://localhost:8006/api/v1/clients/{client_id}/ng-companies/",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if client_ng_response.status_code == 200:
                client_ng_data = client_ng_response.json()
                print(f"\n🚫 クライアント{client_id}のNG企業リスト:")
                
                for ng_company in client_ng_data.get('results', []):
                    print(f"   - 企業名: {ng_company.get('company_name')}")
                    print(f"   - 企業ID: {ng_company.get('company_id')}")
                    print(f"   - マッチ状態: {ng_company.get('matched')}")
                    print(f"   - 理由: {ng_company.get('reason')}")
                    print()

# 全企業の現在の追加状況確認
print("📋 プロジェクト6への企業追加状況:")
project_companies_response = requests.get(
    "http://localhost:8006/api/v1/projects/6/companies/",
    headers={"Authorization": f"Bearer {token}"}
)

if project_companies_response.status_code == 200:
    project_companies = project_companies_response.json()
    print(f"   既に追加済み企業数: {project_companies['count']}")
    
    for company in project_companies['results']:
        print(f"     - ID {company.get('company_id')}: {company.get('company_name')} (ステータス: {company.get('status')})")

# 利用可能企業リストの完全確認
print("\n🔍 利用可能企業リスト（NG判定込み）:")
available_response = requests.get(
    "http://localhost:8006/api/v1/projects/6/available-companies/?page_size=100",
    headers={"Authorization": f"Bearer {token}"}
)

if available_response.status_code == 200:
    available_data = available_response.json()
    print(f"   利用可能企業数: {available_data['count']}")
    
    for company in available_data['results']:
        ng_status = company.get('ng_status', {})
        is_ng = ng_status.get('is_ng', False)
        
        status_text = "🚫 NG" if is_ng else "✅ OK"
        print(f"   {status_text} ID {company['id']}: {company['name']}")
        
        if is_ng:
            print(f"       NG理由: {ng_status}")

print("\n📝 結論:")
print("「自動テスト企業名」が利用可能企業リストに表示されていて、かつNG判定されていない場合、")
print("クライアントNG機能に問題があります。")