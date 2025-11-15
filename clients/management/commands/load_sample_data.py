from datetime import date, timedelta

from django.core.management.base import BaseCommand

from accounts.models import User
from clients.models import Client
from companies.models import Company
from projects.models import Project, ProjectCompany
from masters.models import (
    ProjectProgressStatus,
    ServiceType,
    MediaType,
)


class Command(BaseCommand):
    """Load demo-friendly sample data (companies, clients, projects)."""

    help = 'Load sample data for development/demo use.'

    def handle(self, *args, **options):
        self._ensure_demo_user()
        company_map = self._create_companies()
        client_map = self._create_clients()
        self._create_projects(client_map, company_map)
        self.stdout.write(self.style.SUCCESS('Sample data preparation completed.'))

    def _ensure_demo_user(self):
        user, created = User.objects.get_or_create(
            email='demo@example.com',
            defaults={
                'username': 'demo',
                'name': 'デモユーザー',
                'role': 'user',
                'is_active': True,
            },
        )
        if created:
            user.set_password('password123')
            user.save()
            self.stdout.write('  - created demo@example.com / password123')
        else:
            self.stdout.write('  - demo@example.com already exists')

    def _create_companies(self):
        samples = [
            {
                'name': '株式会社アルファテック',
                'industry': 'IT・ソフトウェア',
                'employee_count': 120,
                'revenue': 500_000_000,
                'prefecture': '東京都',
                'city': '渋谷区',
                'website_url': 'https://alpha-tech.example.com',
                'contact_email': 'info@alpha-tech.example.com',
                'phone': '03-0000-0001',
            },
            {
                'name': 'ベータマーケティング合同会社',
                'industry': 'マーケティング・広告',
                'employee_count': 45,
                'revenue': 150_000_000,
                'prefecture': '大阪府',
                'city': '北区',
                'website_url': 'https://beta-marketing.example.com',
                'contact_email': 'contact@beta-marketing.example.com',
                'phone': '06-0000-0002',
            },
            {
                'name': 'ガンマ製造株式会社',
                'industry': '製造業',
                'employee_count': 320,
                'revenue': 850_000_000,
                'prefecture': '愛知県',
                'city': '名古屋市',
                'website_url': 'https://gamma-factory.example.com',
                'contact_email': 'sales@gamma-factory.example.com',
                'phone': '052-000-0003',
            },
            {
                'name': 'デルタ不動産株式会社',
                'industry': '不動産',
                'employee_count': 80,
                'revenue': 420_000_000,
                'prefecture': '東京都',
                'city': '中央区',
                'website_url': 'https://delta-realestate.example.com',
                'contact_email': 'contact@delta-realestate.example.com',
                'phone': '03-0000-0004',
            },
            {
                'name': 'イプシロン人材サービス',
                'industry': '人材・派遣',
                'employee_count': 65,
                'revenue': 210_000_000,
                'prefecture': '福岡県',
                'city': '福岡市',
                'website_url': 'https://epsilon-hr.example.com',
                'contact_email': 'info@epsilon-hr.example.com',
                'phone': '092-000-0005',
            },
            {
                'name': 'ゼータクラウド株式会社',
                'industry': 'クラウドサービス',
                'employee_count': 150,
                'revenue': 610_000_000,
                'prefecture': '神奈川県',
                'city': '横浜市',
                'website_url': 'https://zeta-cloud.example.com',
                'contact_email': 'hello@zeta-cloud.example.com',
                'phone': '045-000-0006',
            },
            {
                'name': 'シータ物流株式会社',
                'industry': '物流',
                'employee_count': 280,
                'revenue': 430_000_000,
                'prefecture': '北海道',
                'city': '札幌市',
                'website_url': 'https://theta-logistics.example.com',
                'contact_email': 'contact@theta-logistics.example.com',
                'phone': '011-000-0007',
            },
            {
                'name': 'イオタ教育株式会社',
                'industry': '教育',
                'employee_count': 90,
                'revenue': 180_000_000,
                'prefecture': '京都府',
                'city': '京都市',
                'website_url': 'https://iota-education.example.com',
                'contact_email': 'info@iota-education.example.com',
                'phone': '075-000-0008',
            },
            {
                'name': 'カッパヘルスケア株式会社',
                'industry': '医療・ヘルスケア',
                'employee_count': 210,
                'revenue': 720_000_000,
                'prefecture': '兵庫県',
                'city': '神戸市',
                'website_url': 'https://kappa-health.example.com',
                'contact_email': 'support@kappa-health.example.com',
                'phone': '078-000-0009',
            },
            {
                'name': 'ラムダフードサービス',
                'industry': '飲食',
                'employee_count': 55,
                'revenue': 95_000_000,
                'prefecture': '宮城県',
                'city': '仙台市',
                'website_url': 'https://lambda-food.example.com',
                'contact_email': 'sales@lambda-food.example.com',
                'phone': '022-000-0010',
            },
            {
                'name': 'EastCloud株式会社',
                'industry': 'IT・ソフトウェア',
                'employee_count': 85,
                'revenue': 320_000_000,
                'prefecture': '東京都',
                'city': '千代田区',
                'website_url': 'https://east-cloud.jp',
                'contact_email': 'info@east-cloud.jp',
                'phone': '03-6200-0001',
                'corporate_number': '7010001234567',
                'business_description': 'クラウドインフラ運用とデータ連携ソリューションを提供',
            },
        ]

        created = 0
        company_map = {}
        for data in samples:
            company, was_created = Company.objects.update_or_create(
                name=data['name'], defaults=data
            )
            company_map[data['name']] = company
            created += int(was_created)

        self.stdout.write(f'  - companies prepared ({created} created / {len(samples)} total)')
        return company_map

    def _create_clients(self):
        samples = [
            {
                'name': '株式会社アクティブセールス',
                'industry': 'IT・ソフトウェア',
                'contact_person': '田中太郎',
                'contact_person_position': '営業部長',
                'contact_email': 'tanaka@active-sales.example.com',
                'contact_phone': '03-1000-0001',
                'facebook_url': 'https://facebook.com/active-sales',
                'employee_count': 150,
                'revenue': 800_000_000,
                'prefecture': '東京都',
            },
            {
                'name': 'マーケットリンクス株式会社',
                'industry': 'マーケティング・広告',
                'contact_person': '佐藤花子',
                'contact_person_position': 'マーケティング部長',
                'contact_email': 'sato@market-links.example.com',
                'contact_phone': '06-2000-0002',
                'facebook_url': 'https://facebook.com/market-links',
                'employee_count': 80,
                'revenue': 450_000_000,
                'prefecture': '大阪府',
            },
            {
                'name': 'グロースファネル株式会社',
                'industry': 'コンサルティング',
                'contact_person': '鈴木健',
                'contact_person_position': '代表取締役',
                'contact_email': 'suzuki@growth-funnel.example.com',
                'contact_phone': '052-300-0003',
                'facebook_url': 'https://facebook.com/growth-funnel',
                'employee_count': 45,
                'revenue': 280_000_000,
                'prefecture': '愛知県',
            },
            {
                'name': 'ネクストカスタマー株式会社',
                'industry': 'SaaS',
                'contact_person': '山本由紀',
                'contact_person_position': 'カスタマーサクセス部長',
                'contact_email': 'yamamoto@next-customer.example.com',
                'contact_phone': '045-400-0004',
                'facebook_url': 'https://facebook.com/next-customer',
                'employee_count': 120,
                'revenue': 650_000_000,
                'prefecture': '神奈川県',
            },
        ]

        created = 0
        client_map = {}
        for data in samples:
            client, was_created = Client.objects.update_or_create(
                name=data['name'], defaults=data
            )
            client_map[data['name']] = client
            created += int(was_created)

        self.stdout.write(f'  - clients prepared ({created} created / {len(samples)} total)')
        return client_map

    def _create_projects(self, client_map, company_map):
        if not client_map or not company_map:
            self.stdout.write('  - skipped project creation (missing clients or companies)')
            return

        progress_lookup = {p.name: p for p in ProjectProgressStatus.objects.all()}
        service_lookup = {s.name: s for s in ServiceType.objects.all()}
        media_lookup = {m.name: m for m in MediaType.objects.all()}

        today = date.today()
        samples = [
            {
                'name': 'サンプル案件A',
                'client': '株式会社アクティブセールス',
                'status': '進行中',
                'progress_status': '進行中',
                'service_type': 'コンサルティング',
                'media_type': 'LinkedIn',
                'start_offset': -45,
                'description': 'DXコンサルティング支援案件です。',
                'appointment_count': 3,
                'reply_count': 1,
                'companies': ['株式会社アルファテック', 'ゼータクラウド株式会社'],
            },
            {
                'name': '新規プロスペクトリスト生成',
                'client': 'マーケットリンクス株式会社',
                'status': '進行中',
                'progress_status': '着手中',
                'service_type': 'マーケティング支援',
                'media_type': 'Facebook',
                'start_offset': -20,
                'description': '広告配信用のターゲット企業リスト生成を支援。',
                'appointment_count': 5,
                'reply_count': 2,
                'companies': ['ベータマーケティング合同会社', 'カッパヘルスケア株式会社'],
            },
            {
                'name': '営業代行プログラム',
                'client': 'グロースファネル株式会社',
                'status': '進行中',
                'progress_status': '要確認',
                'service_type': '営業代行',
                'media_type': 'LinkedIn',
                'start_offset': -14,
                'description': 'BtoB向け営業の獲得状況を週次でレポート。',
                'appointment_count': 7,
                'reply_count': 4,
                'companies': ['シータ物流株式会社', 'ラムダフードサービス', 'ガンマ製造株式会社'],
            },
            {
                'name': 'カスタマーサクセス立ち上げ支援',
                'client': 'ネクストカスタマー株式会社',
                'status': '進行中',
                'progress_status': '未着手',
                'service_type': 'カスタマーサクセス',
                'media_type': 'Twitter',
                'start_offset': -5,
                'description': 'SaaSプロダクトのオンボーディング体制を整備。',
                'appointment_count': 1,
                'reply_count': 0,
                'companies': ['イオタ教育株式会社'],
            },
            {
                'name': 'リードナーチャリング強化プロジェクト',
                'client': '株式会社アクティブセールス',
                'status': '進行中',
                'progress_status': '修正中',
                'service_type': 'CRM導入',
                'media_type': 'Instagram',
                'start_offset': -60,
                'description': 'MAツール連携とスコアリング精度の改善。',
                'appointment_count': 4,
                'reply_count': 3,
                'companies': ['デルタ不動産株式会社', 'イプシロン人材サービス'],
            },
            {
                'name': 'セールススクリプト刷新',
                'client': 'マーケットリンクス株式会社',
                'status': '進行中',
                'progress_status': '承認待ち',
                'service_type': 'セールス代行',
                'media_type': 'YouTube',
                'start_offset': -30,
                'description': 'インサイドセールス向けスクリプトの改訂作業。',
                'appointment_count': 2,
                'reply_count': 1,
                'companies': ['株式会社アルファテック', 'カッパヘルスケア株式会社'],
            },
        ]

        created = 0
        for sample in samples:
            client = client_map.get(sample['client'])
            if not client:
                continue

            defaults = {
                'client': client,
                'status': sample['status'],
                'start_date': today + timedelta(days=sample['start_offset']),
                'description': sample['description'],
                'appointment_count': sample['appointment_count'],
                'reply_count': sample['reply_count'],
            }

            progress = progress_lookup.get(sample['progress_status'])
            if progress:
                defaults['progress_status'] = progress

            service = service_lookup.get(sample['service_type'])
            if service:
                defaults['service_type'] = service

            media = media_lookup.get(sample['media_type'])
            if media:
                defaults['media_type'] = media

            project, was_created = Project.objects.update_or_create(
                name=sample['name'],
                defaults=defaults,
            )
            created += int(was_created)

            for idx, company_name in enumerate(sample['companies'], start=1):
                company = company_map.get(company_name)
                if not company:
                    continue
                ProjectCompany.objects.update_or_create(
                    project=project,
                    company=company,
                    defaults={
                        'status': '未接触' if idx == 1 else '架電予定',
                        'is_active': True,
                    },
                )

        self.stdout.write(
            f'  - projects prepared ({created} created / {len(samples)} total)'
        )
