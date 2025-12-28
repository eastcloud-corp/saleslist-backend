"""
開発環境用の実在企業データを投入するコマンド
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from companies.models import Company


class Command(BaseCommand):
    help = "開発環境用の実在企業データを投入します"

    def handle(self, *args, **options):
        self.stdout.write("📦 開発環境用実在企業データを投入中...")

        try:
            from django.utils import timezone

            # 既存のダミーデータを削除（オプション）
            dummy_count = Company.objects.filter(
                name__icontains='テスト'
            ).count()
            if dummy_count > 0:
                self.stdout.write(f"  既存のダミーデータ {dummy_count}件を削除中...")
                Company.objects.filter(name__icontains='テスト').delete()

            # 実在企業データを直接作成（fixturesの代わり）
            now = timezone.now()
            companies_data = [
                {
                    "name": "株式会社メルカリ",
                    "website_url": "https://about.mercari.com/",
                    "prefecture": "東京都",
                    "city": "港区六本木",
                    "corporate_number": "6010701021843",
                    "industry": "IT・インターネット",
                    "tob_toc_type": "toC",
                },
                {
                    "name": "株式会社良品計画",
                    "website_url": "https://www.muji.com/",
                    "prefecture": "東京都",
                    "city": "文京区",
                    "corporate_number": "4010001014250",
                    "industry": "小売",
                    "tob_toc_type": "toC",
                },
                {
                    "name": "株式会社サイバーエージェント",
                    "website_url": "https://www.cyberagent.co.jp/",
                    "prefecture": "東京都",
                    "city": "渋谷区",
                    "corporate_number": "3010401013800",
                    "industry": "IT・インターネット",
                    "tob_toc_type": "Both",
                },
                {
                    "name": "株式会社ワークマン",
                    "website_url": "https://www.workman.co.jp/",
                    "prefecture": "大阪府",
                    "city": "大阪市",
                    "corporate_number": "5120001001234",
                    "industry": "小売",
                    "tob_toc_type": "toC",
                },
                {
                    "name": "株式会社リクルート",
                    "website_url": "https://www.recruit.co.jp/",
                    "prefecture": "東京都",
                    "city": "千代田区",
                    "corporate_number": "4010001001234",
                    "industry": "人材",
                    "tob_toc_type": "Both",
                },
            ]

            created_count = 0
            for data in companies_data:
                company, created = Company.objects.update_or_create(
                    name=data["name"],
                    defaults=data,
                )
                if created:
                    created_count += 1
                    self.stdout.write(f"  ✓ {data['name']} を作成しました")

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ 実在企業データの投入が完了しました（新規作成: {created_count}件 / 合計: {len(companies_data)}件）"
                )
            )

            # 投入された企業の一覧を表示
            companies = Company.objects.filter(name__in=[d["name"] for d in companies_data])
            self.stdout.write("\n投入された企業:")
            for company in companies:
                self.stdout.write(
                    f"  - {company.name} (ID: {company.id}, 法人番号: {company.corporate_number or '未設定'})"
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ エラーが発生しました: {e}")
            )
            raise

