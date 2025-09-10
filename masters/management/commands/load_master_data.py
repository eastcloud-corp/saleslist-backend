from django.core.management.base import BaseCommand
from masters.models import (
    ProjectProgressStatus, ServiceType, MediaType,
    RegularMeetingStatus, ListAvailability, ListImportSource
)


class Command(BaseCommand):
    help = '本番環境用マスターデータ投入'

    def handle(self, *args, **options):
        self.stdout.write('🗄️ マスターデータ投入開始...')
        
        # ProjectProgressStatus
        if not ProjectProgressStatus.objects.exists():
            statuses = [
                '未着手', '着手中', '進行中', '一時停止', '完了', '中止',
                '保留', '要確認', '承認待ち', '修正中', 'テスト中',
                '運用開始', 'クローズ', '要見直し'
            ]
            for i, status in enumerate(statuses):
                ProjectProgressStatus.objects.create(
                    name=status,
                    display_order=i
                )
            self.stdout.write(f'✅ ProjectProgressStatus: {len(statuses)}件作成')
        
        # ServiceType
        if not ServiceType.objects.exists():
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
            for i, service in enumerate(service_types):
                ServiceType.objects.create(
                    name=service,
                    display_order=i
                )
            self.stdout.write(f'✅ ServiceType: {len(service_types)}件作成')
        
        # MediaType
        if not MediaType.objects.exists():
            media_types = ['Facebook', 'Instagram', 'Twitter', 'LinkedIn', 'TikTok', 'YouTube']
            for i, media in enumerate(media_types):
                MediaType.objects.create(
                    name=media,
                    display_order=i
                )
            self.stdout.write(f'✅ MediaType: {len(media_types)}件作成')
        
        # RegularMeetingStatus
        if not RegularMeetingStatus.objects.exists():
            meeting_statuses = ['未設定', '週次', '隔週', '月次', '不定期', '停止中']
            for i, status in enumerate(meeting_statuses):
                RegularMeetingStatus.objects.create(
                    name=status,
                    display_order=i
                )
            self.stdout.write(f'✅ RegularMeetingStatus: {len(meeting_statuses)}件作成')
        
        # ListAvailability
        if not ListAvailability.objects.exists():
            availabilities = ['利用可能', '利用不可', '要確認']
            for i, availability in enumerate(availabilities):
                ListAvailability.objects.create(
                    name=availability,
                    display_order=i
                )
            self.stdout.write(f'✅ ListAvailability: {len(availabilities)}件作成')
        
        # ListImportSource
        if not ListImportSource.objects.exists():
            import_sources = ['CSV手動', 'API連携', 'スクレイピング', '外部DB', '手動入力', 'その他']
            for i, source in enumerate(import_sources):
                ListImportSource.objects.create(
                    name=source,
                    display_order=i
                )
            self.stdout.write(f'✅ ListImportSource: {len(import_sources)}件作成')
        
        self.stdout.write('🎉 マスターデータ投入完了!')