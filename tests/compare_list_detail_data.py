#!/usr/bin/env python3
"""
一覧画面vs詳細画面 数字比較テスト
コンサルティング案件Eの数字が一致するかチェック
"""

import requests
import json

# 認証
auth = requests.post("http://localhost:8006/api/v1/auth/login/", json={
    "email": "admin@test.com", "password": "password123"
})
token = auth.json()['access_token']

print("🔍 案件詳細vs一覧 数字比較テスト")
print("="*60)

# 1. 案件一覧画面のデータ（管理モード）
print("1. 案件一覧画面のデータ (management_mode=true)")
list_response = requests.get(
    "http://localhost:8006/api/v1/projects/?management_mode=true",
    headers={"Authorization": f"Bearer {token}"}
)

list_project = None
if list_response.status_code == 200:
    list_data = list_response.json()
    # コンサルティング案件E（ID 6）を探す
    list_project = next((p for p in list_data['results'] if p['id'] == 6), None)
    
    if list_project:
        print(f"  案件名: {list_project['name']}")
        print(f"  アポ数: {list_project.get('appointment_count')}")
        print(f"  承認数: {list_project.get('approval_count')}")
        print(f"  返信数: {list_project.get('reply_count')}")
        print(f"  友達数: {list_project.get('friends_count')}")
        print(f"  企業数: {list_project.get('company_count')}")
        print(f"  状況: {list_project.get('situation')}")
        print(f"  進行状況: {list_project.get('progress_status')}")
        print(f"  ディレクター: {list_project.get('director')}")
        print(f"  運用者: {list_project.get('operator')}")
    else:
        print("  ❌ プロジェクトID 6が見つかりません")

# 2. 案件詳細画面のデータ（管理モード）
print("\n2. 案件詳細画面のデータ (management_mode=true)")
detail_response = requests.get(
    "http://localhost:8006/api/v1/projects/6/?management_mode=true",
    headers={"Authorization": f"Bearer {token}"}
)

detail_project = None
if detail_response.status_code == 200:
    detail_project = detail_response.json()
    print(f"  案件名: {detail_project['name']}")
    print(f"  アポ数: {detail_project.get('appointment_count')}")
    print(f"  承認数: {detail_project.get('approval_count')}")
    print(f"  返信数: {detail_project.get('reply_count')}")
    print(f"  友達数: {detail_project.get('friends_count')}")
    print(f"  企業数: {detail_project.get('company_count', 'MISSING')}")
    print(f"  状況: {detail_project.get('situation')}")
    print(f"  進行状況: {detail_project.get('progress_status')}")
    print(f"  ディレクター: {detail_project.get('director')}")
    print(f"  運用者: {detail_project.get('operator')}")
else:
    print(f"  ❌ 詳細データ取得失敗: {detail_response.status_code}")

# 3. 数字比較
print("\n3. 数字比較結果")
print("="*40)

if list_project and detail_project:
    comparison_fields = [
        'appointment_count', 'approval_count', 'reply_count', 'friends_count',
        'company_count', 'situation', 'progress_status', 'director', 'operator'
    ]
    
    mismatches = []
    
    for field in comparison_fields:
        list_val = list_project.get(field)
        detail_val = detail_project.get(field)
        
        if list_val != detail_val:
            mismatches.append({
                'field': field,
                'list_value': list_val,
                'detail_value': detail_val
            })
            print(f"❌ {field}: 一覧={list_val} vs 詳細={detail_val}")
        else:
            print(f"✅ {field}: {list_val} (一致)")
    
    print(f"\n📊 比較結果サマリー:")
    print(f"  総比較項目: {len(comparison_fields)}")
    print(f"  一致項目: {len(comparison_fields) - len(mismatches)}")
    print(f"  不一致項目: {len(mismatches)}")
    
    if len(mismatches) == 0:
        print("🎉 一覧と詳細のデータが完全に一致しています！")
    else:
        print("⚠️  一覧と詳細のデータに不一致があります")
        
        # 不一致の詳細分析
        print(f"\n🔍 不一致の原因分析:")
        for mismatch in mismatches:
            field = mismatch['field']
            print(f"  {field}:")
            print(f"    - 一覧画面API (ProjectManagementListSerializer): {mismatch['list_value']}")
            print(f"    - 詳細画面API (ProjectManagementDetailSerializer): {mismatch['detail_value']}")
            
            if mismatch['list_value'] is None and mismatch['detail_value'] is not None:
                print(f"    → 一覧用serializerにフィールド不足の可能性")
            elif mismatch['list_value'] is not None and mismatch['detail_value'] is None:
                print(f"    → 詳細用serializerにフィールド不足の可能性")
            else:
                print(f"    → データソースまたは計算ロジックの違い")

else:
    print("❌ データ取得失敗のため比較できませんでした")

print(f"\n💡 推奨アクション:")
print(f"  1. Serializer間でのフィールド一致を確認")
print(f"  2. 計算フィールド（company_count等）のロジック統一")
print(f"  3. フロントエンドでのデータ表示ロジック確認")