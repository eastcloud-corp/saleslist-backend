#!/usr/bin/env python3
"""
フロントエンドNG制御テスト
企業追加画面で実際にNG企業が無効化されているかテスト
"""

import asyncio
import json
from pyppeteer import launch

async def test_ng_company_ui():
    """NG企業UI制御テスト"""
    
    # pyppeteerがない場合はrequestsで確認
    try:
        browser = await launch(headless=True, args=['--no-sandbox'])
    except:
        print("pyppeteer利用不可、APIテストのみ実行")
        return await test_ng_api_only()
    
    page = await browser.newPage()
    
    try:
        print("🔍 フロントエンドNG企業制御テスト")
        
        # 企業追加画面にアクセス
        await page.goto('http://localhost:3007/projects/6/add-companies')
        await page.waitForLoadState('networkidle', timeout=15000)
        
        # 企業リストの読み込み待機
        await page.waitForSelector('.space-y-2', timeout=10000)
        
        # 企業要素を取得
        company_elements = await page.querySelectorAll('.flex.items-center.space-x-3.p-3.rounded-lg.border')
        
        print(f"検出された企業数: {len(company_elements)}")
        
        for i, element in enumerate(company_elements):
            # 企業名取得
            name_element = await element.querySelector('h3.font-medium')
            company_name = await page.evaluate('el => el.textContent', name_element) if name_element else f"企業{i+1}"
            
            # チェックボックス状態確認
            checkbox = await element.querySelector('input[type="checkbox"]')
            is_disabled = False
            if checkbox:
                is_disabled = await page.evaluate('el => el.disabled', checkbox)
            
            # NGバッジ確認
            ng_badge = await element.querySelector('.text-xs:has-text("NG")')
            has_ng_badge = ng_badge is not None
            
            # 背景色確認
            class_name = await page.evaluate('el => el.className', element)
            is_red_bg = 'bg-red-50' in class_name
            
            print(f"\n企業: {company_name}")
            print(f"  チェックボックス無効: {is_disabled}")
            print(f"  NGバッジ: {has_ng_badge}")
            print(f"  赤背景: {is_red_bg}")
            
            # 「自動テスト企業名」の詳細確認
            if company_name == '自動テスト企業名':
                print(f"  ⭐ 問題の企業確認:")
                print(f"    期待: 無効化されているべき")
                print(f"    実際: {'✅ 無効化済み' if is_disabled else '❌ 選択可能（問題）'}")
                
                # クリックテスト
                if not is_disabled:
                    print(f"  🖱️  クリックテスト実行...")
                    try:
                        await checkbox.click()
                        print(f"    結果: クリック成功（問題！）")
                    except Exception as e:
                        print(f"    結果: クリック失敗（正常）- {e}")
        
        await browser.close()
        return True
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        await browser.close()
        return False

async def test_ng_api_only():
    """API経由のNG状態確認のみ"""
    import requests
    
    # 認証
    auth = requests.post("http://localhost:8006/api/v1/auth/login/", 
                        json={"email": "admin@test.com", "password": "password123"})
    token = auth.json()['access_token']
    
    # 利用可能企業取得
    available = requests.get("http://localhost:8006/api/v1/projects/6/available-companies/", 
                            headers={"Authorization": f"Bearer {token}"})
    
    if available.status_code == 200:
        for company in available.json()['results']:
            if company['name'] == '自動テスト企業名':
                ng_status = company.get('ng_status', {})
                print(f"API上の「自動テスト企業名」:")
                print(f"  ng_status.is_ng: {ng_status.get('is_ng', False)}")
                print(f"  ng_status.types: {ng_status.get('types', [])}")
                
                if ng_status.get('is_ng', False):
                    print("✅ API上では正しくNG判定されています")
                    print("❌ フロントエンドの無効化処理に問題があります")
                else:
                    print("❌ API上でNG判定されていません")
                break
    
    return True

if __name__ == "__main__":
    asyncio.run(test_ng_company_ui())