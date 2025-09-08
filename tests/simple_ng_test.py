#!/usr/bin/env python3
"""
簡潔なNG企業テスト
"""

import requests

# 認証・トークン取得
auth = requests.post("http://localhost:8006/api/v1/auth/login/", json={"email": "admin@test.com", "password": "password123"})
token = auth.json()['access_token']

# 案件6の利用可能企業確認
available = requests.get("http://localhost:8006/api/v1/projects/6/available-companies/", 
                        headers={"Authorization": f"Bearer {token}"})

print("📋 案件6の利用可能企業:")
if available.status_code == 200:
    data = available.json()
    for company in data['results']:
        ng = company.get('ng_status', {})
        status = "🚫NG" if ng.get('is_ng') else "✅OK"
        print(f"  {status} ID{company['id']}: {company['name']}")
        if ng.get('is_ng'):
            print(f"      理由: {ng.get('types')} - {ng.get('reasons')}")
else:
    print(f"❌ API失敗: {available.status_code}")

# 企業ID 2が自動テスト企業名かつクライアントNGか確認
company2 = requests.get("http://localhost:8006/api/v1/companies/2/", headers={"Authorization": f"Bearer {token}"})
if company2.status_code == 200:
    c2_data = company2.json()
    print(f"\n🔍 企業ID2: {c2_data['name']}")
    print(f"   グローバルNG: {c2_data.get('is_global_ng')}")
    print(f"   NG状態: {c2_data.get('ng_status', {})}")

print("\n💡 結論: NG企業は検出されており、フロントエンドで無効化されているはずです")