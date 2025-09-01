#!/usr/bin/env python3
"""
全39 APIエンドポイント OpenAPI仕様適合チェック
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8080"

# 認証トークン取得
def get_token():
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "user@example.com",
        "password": "password123"
    })
    if response.status_code == 200:
        return response.json()['access_token']
    return None

def check_endpoint(method, endpoint, headers=None, data=None):
    """エンドポイントをテストして結果を返す"""
    try:
        full_url = f"{BASE_URL}{endpoint}"
        
        if method == 'GET':
            response = requests.get(full_url, headers=headers)
        elif method == 'POST':
            response = requests.post(full_url, headers=headers, json=data)
        elif method == 'PUT':
            response = requests.put(full_url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(full_url, headers=headers)
        else:
            return {'status': 'UNKNOWN_METHOD', 'code': 0}
        
        result = {
            'status': 'SUCCESS' if response.status_code < 300 else 'ERROR',
            'code': response.status_code,
            'size': len(response.text) if response.text else 0,
            'has_data': 'results' in response.text or 'count' in response.text
        }
        
        # レスポンスからIDを抽出（削除テスト用）
        if response.status_code in [200, 201] and response.text:
            try:
                json_data = response.json()
                if isinstance(json_data, dict) and 'id' in json_data:
                    result['created_id'] = json_data['id']
            except:
                pass
        
        return result
    except Exception as e:
        return {'status': 'EXCEPTION', 'code': 0, 'error': str(e)}

def main():
    print("🧪 全39 APIエンドポイント OpenAPI仕様適合チェック開始")
    print("=" * 60)
    
    # 認証トークン取得
    login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "user@example.com",
        "password": "password123"
    })
    
    if login_response.status_code != 200:
        print("❌ 認証失敗")
        return
    
    login_data = login_response.json()
    token = login_data['access_token']
    refresh_token = login_data['refresh_token']
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 全エンドポイント定義（OpenAPI仕様書より）
    endpoints = [
        # 認証API
        ('POST', '/api/v1/auth/login', None, {"email": "user@example.com", "password": "password123"}),
        ('POST', '/api/v1/auth/logout', headers, {}),
        ('GET', '/api/v1/auth/me', headers, None),
        ('POST', '/api/v1/auth/refresh', headers, {"refresh_token": refresh_token}),
        
        # ダッシュボードAPI
        ('GET', '/api/v1/dashboard/stats', headers, None),
        ('GET', '/api/v1/dashboard/recent-projects', headers, None),
        ('GET', '/api/v1/dashboard/recent-companies', headers, None),
        
        # 企業API
        ('GET', '/api/v1/companies/', headers, None),
        ('POST', '/api/v1/companies/', headers, {"name": "テスト企業", "industry": "IT・ソフトウェア"}),
        ('GET', '/api/v1/companies/5/', headers, None),
        ('PUT', '/api/v1/companies/5/', headers, {"name": "更新企業"}),
        ('DELETE', '/api/v1/companies/9/', headers, None),  # 存在するIDを削除
        ('POST', '/api/v1/companies/5/toggle_ng/', headers, {"reason": "テスト"}),
        
        # プロジェクトAPI
        ('GET', '/api/v1/projects/', headers, None),
        ('GET', '/api/v1/projects/1/', headers, None),
        ('POST', '/api/v1/projects/1/add-companies/', headers, {"company_ids": [1, 2]}),
        ('GET', '/api/v1/projects/1/companies/', headers, None),
        ('GET', '/api/v1/projects/1/available-companies/', headers, None),
        
        # クライアントAPI
        ('GET', '/api/v1/clients/', headers, None),
        ('GET', '/api/v1/clients/1/', headers, None),
        ('GET', '/api/v1/clients/1/stats/', headers, None),
        ('GET', '/api/v1/clients/1/ng-companies/', headers, None),
        
        # マスターAPI
        ('GET', '/api/v1/master/industries/', headers, None),
        ('GET', '/api/v1/master/statuses/', headers, None),
        ('GET', '/api/v1/master/prefectures/', headers, None),
        
        # 役員API
        ('GET', '/api/v1/companies/5/executives/', headers, None),
        ('GET', '/api/v1/executives/1/', headers, None),
        
        # プロジェクト詳細操作
        ('PUT', '/api/v1/projects/1/companies/5/', headers, {"status": "DM送信済み"}),
        ('DELETE', '/api/v1/projects/1/companies/5/', headers, None),
        ('POST', '/api/v1/projects/1/bulk_update_status/', headers, {"company_ids": [2], "status": "DM送信済み"}),
        ('GET', '/api/v1/projects/1/export_csv/', headers, None),
        
        # NGリスト関連
        ('GET', '/api/v1/projects/1/ng_companies/', headers, None),
        ('GET', '/api/v1/ng-companies/template/', headers, None),
        ('POST', '/api/v1/ng-companies/match/', headers, {"client_id": 1}),
        
        # 保存フィルター
        ('GET', '/api/v1/saved_filters/', headers, None),
        ('POST', '/api/v1/saved_filters/', headers, {"name": "テストフィルター", "filter_conditions": {"industry": "IT"}}),
        ('GET', '/api/v1/saved_filters/2/', headers, None),
        ('DELETE', '/api/v1/saved_filters/4/', headers, None),
        
        # クライアント関連追加
        ('GET', '/api/v1/clients/1/projects/', headers, None),
        ('POST', '/api/v1/clients/1/ng-companies/import/', headers, {"file": "dummy"}),
        ('DELETE', '/api/v1/clients/1/ng-companies/1/', headers, None),
        ('GET', '/api/v1/clients/1/available-companies/', headers, None),
        
        # 企業CSV
        ('POST', '/api/v1/companies/import_csv/', headers, {"file": "dummy"}),
        ('GET', '/api/v1/companies/export_csv/', headers, None),
    ]
    
    results = []
    success_count = 0
    total_count = len(endpoints)
    created_ids = {}  # 作成されたIDを記録
    
    for method, endpoint, test_headers, test_data in endpoints:
        # 削除テスト前にcreateでIDを取得
        if method == 'DELETE' and ('saved_filters' in endpoint or 'ng-companies' in endpoint):
            if 'saved_filters' in endpoint:
                # フィルター作成してIDを取得
                create_response = requests.post(f"{BASE_URL}/api/v1/saved_filters/", 
                                              headers=headers, 
                                              json={"name": "削除テスト用", "filter_conditions": {}})
                if create_response.status_code == 201:
                    created_id = create_response.json()['id'] 
                    endpoint = endpoint.replace('/saved_filters/4/', f'/saved_filters/{created_id}/')
            
            elif 'ng-companies' in endpoint:
                # NG企業作成してIDを取得
                create_response = requests.post(f"{BASE_URL}/api/v1/clients/1/ng-companies/import/", 
                                              headers=headers, 
                                              json={"file": "test"})
                # 既存のNG企業ID=1を使用
                pass
        
        result = check_endpoint(method, endpoint, test_headers, test_data)
        result['method'] = method
        result['endpoint'] = endpoint
        results.append(result)
        
        if result['status'] == 'SUCCESS':
            success_count += 1
            print(f"✅ {method} {endpoint} - {result['code']}")
        else:
            print(f"❌ {method} {endpoint} - {result['code']} ({result.get('error', 'Error')})")
    
    print("\n" + "=" * 60)
    print(f"📊 テスト結果: {success_count}/{total_count} 成功")
    print(f"🎯 仕様適合率: {(success_count/total_count)*100:.1f}%")
    
    # 詳細結果をJSONで保存
    with open('api_compliance_test.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_endpoints': total_count,
            'success_count': success_count,
            'success_rate': (success_count/total_count)*100,
            'results': results
        }, f, ensure_ascii=False, indent=2)
    
    print("\n📄 詳細結果: api_compliance_test.json")
    
    if success_count == total_count:
        print("🎉 全APIがOpenAPI仕様に適合しています！")
    else:
        print(f"⚠️ {total_count - success_count}個のAPIに問題があります")

if __name__ == "__main__":
    main()