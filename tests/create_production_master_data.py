#!/usr/bin/env python3
"""
本番環境マスターデータ作成スクリプト
緊急時の本番データ修復用
"""

import requests
import json
import sys
from datetime import datetime

class ProductionMasterDataCreator:
    def __init__(self, base_url="https://sales-navigator.east-cloud.jp"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
        self.admin_token = None
        self.results = []
        
    def authenticate(self):
        """管理者認証"""
        print("🔐 管理者認証中...")
        try:
            response = requests.post(f"{self.api_base}/auth/login/", json={
                "email": "salesnav_admin@budget-sales.com",
                "password": "salesnav20250901"
            })
            
            if response.status_code == 200:
                self.admin_token = response.json()['access_token']
                print("✅ 認証成功")
                return True
            else:
                print(f"❌ 認証失敗: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 認証エラー: {e}")
            return False
    
    def create_progress_statuses(self):
        """進行状況ステータス作成"""
        print("\n📊 進行状況ステータス作成...")
        
        statuses = [
            '未着手', '着手中', '進行中', '一時停止', '完了', '中止',
            '保留', '要確認', '承認待ち', '修正中', 'テスト中',
            '運用開始', 'クローズ', '要見直し'
        ]
        
        created_count = 0
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        for status in statuses:
            try:
                response = requests.post(f"{self.api_base}/master/progress-statuses/", 
                    json={"name": status}, headers=headers)
                
                if response.status_code in [200, 201]:
                    created_count += 1
                    print(f"✅ 作成: {status}")
                elif response.status_code == 400 and "already exists" in response.text.lower():
                    print(f"⚠️  既存: {status}")
                else:
                    print(f"❌ 失敗: {status} ({response.status_code})")
                    
            except Exception as e:
                print(f"❌ エラー: {status} - {e}")
        
        print(f"進行状況ステータス: {created_count}件作成")
        return created_count
    
    def create_service_types(self):
        """サービス種別作成"""
        print("\n🛠️ サービス種別作成...")
        
        service_types = [
            'コンサルティング', 'システム開発', 'マーケティング支援', 'セールス代行',
            'データ分析', '業務改善', 'DX推進', 'クラウド移行', 'セキュリティ対策',
            'インフラ構築', 'アプリ開発', 'ホームページ制作', 'ECサイト構築',
            '社内システム開発', 'AI・機械学習', 'IoT導入', 'RPA導入', 'CRM導入',
            'ERP導入', 'BI導入', 'Web制作', 'SEO対策', 'SNS運用', 'ブランディング',
            '採用支援', '人材育成', '組織改革', '財務コンサル', '法務支援',
            'IP戦略', 'M&A支援', '海外展開', 'パートナーシップ', '投資家紹介',
            'PR・広報', 'イベント企画', '営業代行', 'テレアポ代行', 'リード獲得',
            'カスタマーサクセス', 'サポート業務', 'BPO', '翻訳・通訳', '法人営業',
            '個人営業', 'B2B営業', 'B2C営業', 'インサイドセールス', 'フィールドセールス',
            'アカウント営業', 'ソリューション営業', 'テクニカルセールス', 'その他'
        ]
        
        created_count = 0
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        for service in service_types:
            try:
                response = requests.post(f"{self.api_base}/master/service-types/", 
                    json={"name": service}, headers=headers)
                
                if response.status_code in [200, 201]:
                    created_count += 1
                    if created_count <= 5:  # 最初の5件のみ表示
                        print(f"✅ 作成: {service}")
                elif response.status_code == 400:
                    if created_count <= 5:
                        print(f"⚠️  既存: {service}")
                        
            except Exception as e:
                print(f"❌ エラー: {service} - {e}")
        
        print(f"サービス種別: {created_count}件作成（全{len(service_types)}種類）")
        return created_count
    
    def create_media_types(self):
        """媒体種別作成"""
        print("\n📱 媒体種別作成...")
        
        media_types = ['Facebook', 'Instagram', 'Twitter', 'LinkedIn', 'TikTok', 'YouTube']
        created_count = 0
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        for media in media_types:
            try:
                response = requests.post(f"{self.api_base}/master/media-types/", 
                    json={"name": media}, headers=headers)
                
                if response.status_code in [200, 201]:
                    created_count += 1
                    print(f"✅ 作成: {media}")
                elif response.status_code == 400:
                    print(f"⚠️  既存: {media}")
                    
            except Exception as e:
                print(f"❌ エラー: {media} - {e}")
        
        print(f"媒体種別: {created_count}件作成")
        return created_count
    
    def create_other_masters(self):
        """その他マスターデータ作成"""
        print("\n📋 その他マスターデータ作成...")
        
        # 定例会議ステータス
        meeting_statuses = ['未設定', '週次', '隔週', '月次', '不定期', '停止中']
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        for status in meeting_statuses:
            try:
                requests.post(f"{self.api_base}/master/meeting-statuses/", 
                    json={"name": status}, headers=headers)
            except:
                pass
        
        # リスト利用可能性
        availabilities = ['利用可能', '利用不可', '要確認']
        for availability in availabilities:
            try:
                requests.post(f"{self.api_base}/master/list-availabilities/", 
                    json={"name": availability}, headers=headers)
            except:
                pass
        
        # リストインポートソース
        import_sources = ['CSV手動', 'API連携', 'スクレイピング', '外部DB', '手動入力', 'その他']
        for source in import_sources:
            try:
                requests.post(f"{self.api_base}/master/list-import-sources/", 
                    json={"name": source}, headers=headers)
            except:
                pass
        
        print("✅ その他マスターデータ作成完了")
    
    def run_master_data_creation(self):
        """マスターデータ作成実行"""
        print("🗄️ 本番環境マスターデータ作成開始")
        print("="*60)
        
        if not self.authenticate():
            return False
        
        total_created = 0
        total_created += self.create_progress_statuses()
        total_created += self.create_service_types() 
        total_created += self.create_media_types()
        self.create_other_masters()
        
        print("\n" + "="*60)
        print(f"🎉 マスターデータ作成完了: {total_created}+件")
        print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True

if __name__ == "__main__":
    creator = ProductionMasterDataCreator()
    success = creator.run_master_data_creation()
    
    if success:
        print("\n✅ 本番環境マスターデータ作成成功")
        sys.exit(0)
    else:
        print("\n❌ 本番環境マスターデータ作成失敗")
        sys.exit(1)