from django.core.management.base import BaseCommand
from masters.models import (
    Industry, ProjectProgressStatus, ServiceType, MediaType,
    RegularMeetingStatus, ListAvailability, ListImportSource
)


class Command(BaseCommand):
    help = '本番環境用マスターデータ投入'

    def handle(self, *args, **options):
        self.stdout.write('🗄️ マスターデータ投入開始...')
        # Industry - 階層構造対応（常に最新の状態を保つため、存在チェックなしでget_or_createを実行）
        # 業界カテゴリ（親業界）
        industry_categories = [
            ("小売・卸売", 1),
            ("飲食・宿泊", 2),
            ("サービス", 3),
            ("IT・マスコミ", 4),
            ("コンサルティング・専門サービス", 5),
            ("人材", 6),
            ("医療・福祉", 7),
            ("不動産", 8),
            ("金融", 9),
            ("教育・学習", 10),
            ("建設・建築", 11),
            ("運輸・物流", 12),
            ("製造業", 13),
            ("エネルギー", 14),
            ("農林水産", 15),
            ("鉱業", 16),
            ("官公庁", 17),
            ("団体・NPO", 18),
            ("NPO", 19),
            ("その他", 20),
            ("未分類", 21),
        ]
        
        # 業種（子業界）の定義
        sub_industries_data = {
            "小売・卸売": [
                "百貨店", "スーパー", "コンビニ", "食料品", "酒屋",
                "ファッション、洋服", "書籍、文房具、がん具", "医薬品、化粧品",
                "自動車、自転車", "電器", "家具、インテリア", "ガソリンスタンド、燃料",
                "日用雑貨", "建築、鉱物、金属", "機械器具", "総合卸売、商社、貿易",
                "通信販売", "その他小売、卸売",
            ],
            "飲食・宿泊": [
                "食堂、レストラン", "居酒屋、バー", "喫茶店", "ファーストフード",
                "持ち帰り、デリバリー", "旅館、ホテル",
            ],
            "サービス": [
                "旅行、レジャー", "床屋、美容院", "エステ、リラクゼーション", "ペット",
                "リース、レンタル", "ビル管理、オフィスサポート", "その他サービス",
            ],
            "IT・マスコミ": [
                "情報通信、インターネット", "ソフトウェア、SI", "デザイン、製作",
                "広告、販促", "放送、出版、マスコミ",
            ],
            "コンサルティング・専門サービス": [
                "経営コンサルティング", "会計、税務、法務、労務",
            ],
            "人材": ["人材"],
            "医療・福祉": [
                "病院", "医院、診療所", "歯医者", "動物病院", "介護、福祉",
            ],
            "不動産": [
                "不動産売買", "不動産賃貸", "不動産開発",
            ],
            "金融": [
                "銀行", "貸金業、クレジットカード", "金融商品取引", "保険", "その他金融",
            ],
            "教育・学習": [
                "幼稚園、保育園", "小学校、中学校", "高校", "大学", "専門学校",
                "予備校", "進学塾、学習塾", "外国語会話", "パソコンスクール",
                "幼児教室", "その他教室、スクール",
            ],
            "建設・建築": [
                "総合（建設・建築）", "専門（建設・建築）", "設備（建設・建築）",
            ],
            "運輸・物流": [
                "運輸", "倉庫", "運輸付帯サービス",
            ],
            "製造業": [
                "食料品・飲料", "たばこ", "飼料", "繊維工業", "衣服、繊維",
                "パルプ、紙", "印刷", "油脂加工、洗剤、塗料", "化粧品", "医薬品",
                "その他の化学工業", "プラスチック製品", "ゴム製品", "一般機械",
                "電気、電子機器", "自動車、輸送機器", "精密機械", "鉄、金属", "その他製造業",
            ],
            "エネルギー": [
                "電気", "ガス", "水道",
            ],
            "農林水産": ["農林水産"],
            "鉱業": ["鉱業"],
            "官公庁": ["官公庁"],
            "団体・NPO": [
                "組合", "団体", "協会",
            ],
            "NPO": ["NPO"],
            # 「その他」と「未分類」はカテゴリとしてのみ作成（子業界として作成しない）
        }
        
        # 業界カテゴリを作成
        category_map = {}
        created_count = 0
        updated_count = 0
        for name, order in industry_categories:
            industry, created = Industry.objects.get_or_create(
                name=name,
                defaults={
                    'display_order': order,
                    'is_category': True,
                    'parent_industry': None
                }
            )
            category_map[name] = industry
            if created:
                created_count += 1
            else:
                # 既存データの更新
                needs_update = False
                if not industry.is_category:
                    industry.is_category = True
                    needs_update = True
                if industry.parent_industry is not None:
                    industry.parent_industry = None
                    needs_update = True
                if industry.display_order != order:
                    industry.display_order = order
                    needs_update = True
                if needs_update:
                    industry.save()
                    updated_count += 1
        
        # 業種（子業界）を作成（各カテゴリ内でdisplay_orderを1から始める）
        sub_created_count = 0
        sub_updated_count = 0
        for category_name, sub_names in sub_industries_data.items():
            parent = category_map.get(category_name)
            if not parent:
                continue
            
            # 各カテゴリ内でdisplay_orderを1から始める
            sub_order = 1
            for sub_name in sub_names:
                sub_industry, created = Industry.objects.get_or_create(
                    name=sub_name,
                    defaults={
                        'display_order': sub_order,
                        'is_category': False,
                        'parent_industry': parent
                    }
                )
                if created:
                    sub_created_count += 1
                else:
                    # 既存データの更新
                    needs_update = False
                    if sub_industry.is_category:
                        sub_industry.is_category = False
                        needs_update = True
                    if sub_industry.parent_industry != parent:
                        sub_industry.parent_industry = parent
                        needs_update = True
                    if sub_industry.display_order != sub_order:
                        sub_industry.display_order = sub_order
                        needs_update = True
                    if needs_update:
                        sub_industry.save()
                        sub_updated_count += 1
                sub_order += 1
        
        total_created = created_count + sub_created_count
        total_updated = updated_count + sub_updated_count
        self.stdout.write(
            f'✅ Industry: カテゴリ {created_count}件作成/{updated_count}件更新, '
            f'業種 {sub_created_count}件作成/{sub_updated_count}件更新 '
            f'(合計 {total_created}件作成/{total_updated}件更新)'
        )

        # ProjectProgressStatus - 常に最新の状態を保つため、存在チェックなしでget_or_createを実行
        statuses = [
            '未着手', '着手中', '進行中', '一時停止', '完了', '中止',
            '保留', '要確認', '承認待ち', '修正中', 'テスト中',
            '運用開始', 'クローズ', '要見直し'
        ]
        created_count = 0
        updated_count = 0
        for i, status in enumerate(statuses):
            obj, created = ProjectProgressStatus.objects.get_or_create(
                name=status,
                defaults={'display_order': i}
            )
            if created:
                created_count += 1
            elif obj.display_order != i:
                # 既存レコードのdisplay_orderを更新
                obj.display_order = i
                obj.save(update_fields=['display_order'])
                updated_count += 1
        self.stdout.write(f'✅ ProjectProgressStatus: {created_count}件作成, {updated_count}件更新')
        
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
