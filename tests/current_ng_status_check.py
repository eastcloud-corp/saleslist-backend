#!/usr/bin/env python3
"""
現在のNG状況確認
「自動テスト企業名」がクライアントNGリストにあるのに、企業追加で選択できる問題を調査
"""

import requests

# 認証
auth = requests.post("http://localhost:8006/api/v1/auth/login/", json={"email": "admin@test.com", "password": "password123"})
token = auth.json()['access_token']

print("🔍 現在のNG状況確認")
print("="*50)

# 1. クライアント1のNGリスト確認
print("1. クライアント1のNGリスト:")
client_ng = requests.get("http://localhost:8006/api/v1/clients/1/ng-companies/", 
                        headers={"Authorization": f"Bearer {token}"})

client_ng_companies = []
if client_ng.status_code == 200:
    for ng in client_ng.json().get('results', []):
        print(f"  - 企業名: {ng.get('company_name')}")
        print(f"  - 企業ID: {ng.get('company_id')}")  
        print(f"  - マッチ状態: {ng.get('matched')}")
        client_ng_companies.append(ng)

# 2. 案件6の利用可能企業リスト確認
print("\n2. 案件6の利用可能企業:")
available = requests.get("http://localhost:8006/api/v1/projects/6/available-companies/", 
                        headers={"Authorization": f"Bearer {token}"})

if available.status_code == 200:
    companies = available.json()['results']
    print(f"  利用可能企業数: {len(companies)}")
    
    for company in companies:
        ng_status = company.get('ng_status', {})
        is_ng = ng_status.get('is_ng', False)
        ng_types = ng_status.get('types', [])
        
        print(f"\n  企業ID {company['id']}: {company['name']}")
        print(f"    is_global_ng: {company.get('is_global_ng', False)}")
        print(f"    ng_status.is_ng: {is_ng}")
        print(f"    ng_status.types: {ng_types}")
        
        # 「自動テスト企業名」の場合、詳細確認
        if company['name'] == '自動テスト企業名':
            print(f"    ⭐ これが問題の企業です")
            print(f"    NG判定されているか: {'❌ NG' if is_ng else '✅ 選択可能'}")
            
            # クライアントNGリストとの照合
            matching_ng = None
            for client_ng in client_ng_companies:
                if (client_ng.get('company_id') == company['id'] or 
                    client_ng.get('company_name') == company['name']):
                    matching_ng = client_ng
                    break
            
            if matching_ng:
                print(f"    クライアントNGリストの対応:")
                print(f"      - NGリスト企業名: {matching_ng.get('company_name')}")
                print(f"      - NGリスト企業ID: {matching_ng.get('company_id')}")
                print(f"      - マッチ状態: {matching_ng.get('matched')}")
                print(f"    🔍 問題: マッチ状態が{matching_ng.get('matched')}なのにNG判定されていない")
            else:
                print(f"    ❌ クライアントNGリストに対応するレコードが見つからない")

# 3. client_ng_companies テーブルの直接確認（Django shell経由）
print("\n3. バックエンドでの詳細確認が必要:")
print("   python manage.py shell で以下を実行してください:")
print("   from clients.models import Client")
print("   from companies.models import Company") 
print("   client = Client.objects.get(id=1)")
print("   client.ng_companies.all()")
print("   # matched=Trueでcompany_id=2のレコードがあるか確認")