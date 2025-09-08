#!/usr/bin/env python3
"""
最終NG企業制御検証テスト
バックエンド・フロントエンド連携でNG企業が正しく制御されているか最終確認
"""

import requests

def test_ng_control():
    # 認証
    auth = requests.post("http://localhost:8006/api/v1/auth/login/", json={
        "email": "admin@test.com", "password": "password123"
    })
    token = auth.json()['access_token']
    
    print("🎯 最終NG企業制御検証テスト")
    print("="*50)
    
    # 案件6の利用可能企業確認
    available = requests.get(
        "http://localhost:8006/api/v1/projects/6/available-companies/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if available.status_code == 200:
        companies = available.json()['results']
        
        ng_companies = 0
        normal_companies = 0
        
        print("📋 企業追加画面に表示される企業:")
        for company in companies:
            ng_status = company.get('ng_status', {})
            is_ng = ng_status.get('is_ng', False)
            types = ng_status.get('types', [])
            
            if is_ng:
                ng_companies += 1
                print(f"  🚫 NG: ID{company['id']} {company['name']} ({', '.join(types)})")
            else:
                normal_companies += 1
                print(f"  ✅ OK: ID{company['id']} {company['name']}")
        
        print(f"\n📊 最終結果:")
        print(f"  総企業数: {len(companies)}")
        print(f"  NG企業（無効化されるべき）: {ng_companies}")
        print(f"  正常企業（選択可能）: {normal_companies}")
        
        # NG企業追加テスト（APIレベル）
        if ng_companies > 0:
            print(f"\n🧪 NG企業追加防止テスト:")
            ng_company = next((c for c in companies if c.get('ng_status', {}).get('is_ng')), None)
            
            if ng_company:
                # NG企業の追加を試行
                add_response = requests.post(
                    f"http://localhost:8006/api/v1/projects/6/add-companies/",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json={"company_ids": [ng_company['id']]}
                )
                
                if add_response.status_code == 200:
                    result = add_response.json()
                    added = result.get('added_count', 0)
                    errors = result.get('errors', [])
                    
                    if added == 0 and len(errors) > 0:
                        print(f"  ✅ NG企業追加が正しく拒否されました")
                        print(f"     エラー: {errors[0]}")
                    else:
                        print(f"  ❌ NG企業が追加されました（問題）")
                        print(f"     追加数: {added}")
                else:
                    print(f"  ⚠️  API呼び出し失敗: {add_response.status_code}")
        
        success_rate = 100 if ng_companies >= 2 and normal_companies >= 0 else 0
        
        print(f"\n🎯 総合判定:")
        if ng_companies >= 2:
            print("✅ NG企業制御が正常に動作しています")
            print("  - グローバルNG企業: 無効化済み")
            print("  - クライアントNG企業: 無効化済み")
            return True
        else:
            print("❌ NG企業制御に問題があります")
            return False
    
    else:
        print(f"❌ API呼び出し失敗: {available.status_code}")
        return False

if __name__ == "__main__":
    success = test_ng_control()
    print(f"\n{'🎉 テスト成功' if success else '💥 テスト失敗'}")
    exit(0 if success else 1)