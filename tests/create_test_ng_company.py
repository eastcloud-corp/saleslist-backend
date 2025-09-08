#!/usr/bin/env python3
"""
テスト用NG企業作成
クライアントNG機能テスト用の新しい企業を作成
"""

import requests

# 認証
auth = requests.post("http://localhost:8006/api/v1/auth/login/", json={
    "email": "admin@test.com", "password": "password123"
})
token = auth.json()['access_token']

print("🏗️  テスト用NG企業作成")

# 新しい企業を作成
new_company = {
    "name": "NGテスト企業",
    "industry": "IT・ソフトウェア",
    "employee_count": 100,
    "revenue": 500000000,
    "prefecture": "東京都",
    "city": "渋谷区",
    "established_year": 2020,
    "website_url": "https://ng-test.com",
    "contact_email": "test@ng-test.com",
    "phone": "03-9999-9999"
}

create_response = requests.post(
    "http://localhost:8006/api/v1/companies/",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    },
    json=new_company
)

if create_response.status_code == 201:
    created_company = create_response.json()
    company_id = created_company['id']
    print(f"✅ 新企業作成成功: ID{company_id} {created_company['name']}")
    
    # クライアント1のNGリストに追加
    ng_add_response = requests.post(
        "http://localhost:8006/api/v1/clients/1/ng-companies/",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "company_name": "NGテスト企業",
            "company_id": company_id,
            "reason": "テスト用NG企業"
        }
    )
    
    if ng_add_response.status_code == 201:
        print("✅ クライアントNGリストに追加成功")
    else:
        print(f"❌ NGリスト追加失敗: {ng_add_response.status_code}")
        print(ng_add_response.text)
    
    # 案件6への追加テスト
    print("\n🧪 NG企業追加テスト:")
    add_test_response = requests.post(
        f"http://localhost:8006/api/v1/projects/6/add-companies/",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={"company_ids": [company_id]}
    )
    
    if add_test_response.status_code == 200:
        result = add_test_response.json()
        added = result.get('added_count', 0)
        errors = result.get('errors', [])
        
        print(f"追加結果: {added}社追加, エラー: {len(errors)}件")
        
        if added == 0 and len(errors) > 0:
            print("✅ NG企業追加が正しく拒否されました")
            print(f"エラーメッセージ: {errors[0]}")
        else:
            print("❌ NG企業が追加されました（問題）")
    
else:
    print(f"❌ 企業作成失敗: {create_response.status_code}")
    print(create_response.text)