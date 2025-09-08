#!/usr/bin/env python3
"""
NG企業機能テスト
NG企業が正しく判定・除外されているかテスト
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

# プロジェクトID 6の利用可能企業リスト取得
available_response = requests.get(
    "http://localhost:8006/api/v1/projects/6/available-companies/?limit=10",
    headers={"Authorization": f"Bearer {token}"}
)

if available_response.status_code != 200:
    print(f"❌ 利用可能企業取得失敗: {available_response.status_code}")
    print(available_response.text)
    exit(1)

data = available_response.json()
print(f"✅ 利用可能企業取得成功: {data['count']}件")

# NG情報チェック
ng_companies = []
normal_companies = []

for company in data['results']:
    ng_status = company.get('ng_status', {})
    
    print(f"\n🔍 企業ID {company['id']}: {company['name']}")
    print(f"  is_global_ng: {company.get('is_global_ng', False)}")
    print(f"  ng_status: {ng_status}")
    
    if ng_status.get('is_ng', False):
        ng_companies.append(company)
        print(f"  ➜ NG企業（理由: {ng_status.get('reason', 'unknown')}）")
    else:
        normal_companies.append(company)
        print(f"  ➜ 正常企業")

print(f"\n📊 NG企業判定結果:")
print(f"総企業数: {len(data['results'])}")
print(f"NG企業: {len(ng_companies)}件")
print(f"正常企業: {len(normal_companies)}件")

# NG企業設定の確認
if len(ng_companies) == 0:
    print("\n⚠️  NG企業が設定されていません。テスト用NG企業を設定しますか？")
    
    # 最初の企業をグローバルNGに設定
    if normal_companies:
        test_company = normal_companies[0]
        ng_response = requests.patch(
            f"http://localhost:8006/api/v1/companies/{test_company['id']}/",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={"is_global_ng": True}
        )
        
        if ng_response.status_code == 200:
            print(f"✅ テスト用NG企業設定完了: {test_company['name']} (ID: {test_company['id']})")
            
            # 再度利用可能企業リスト取得
            recheck_response = requests.get(
                "http://localhost:8006/api/v1/projects/6/available-companies/?limit=10",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if recheck_response.status_code == 200:
                recheck_data = recheck_response.json()
                updated_company = next((c for c in recheck_data['results'] if c['id'] == test_company['id']), None)
                
                if updated_company:
                    updated_ng_status = updated_company.get('ng_status', {})
                    print(f"🔍 更新後のNG状態: {updated_ng_status}")
                    
                    if updated_ng_status.get('is_ng', False):
                        print("✅ NG企業判定が正常に動作しています")
                    else:
                        print("❌ NG企業判定が動作していません")
        else:
            print(f"❌ NG企業設定失敗: {ng_response.status_code}")
else:
    print("✅ NG企業が正しく設定されています")

print(f"\n📝 結論:")
if len(ng_companies) > 0:
    print("NG企業は検出されており、フロントエンドでグレーアウト・無効化されているはずです")
    print("もしNG企業が選択可能な場合、フロントエンドの実装に問題があります")
else:
    print("NG企業が検出されていません。NG設定またはAPI実装に問題があります")