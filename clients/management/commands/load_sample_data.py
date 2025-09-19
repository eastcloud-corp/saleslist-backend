from datetime import date

from django.core.management.base import BaseCommand

from accounts.models import User
from clients.models import Client
from companies.models import Company
from projects.models import Project, ProjectCompany


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
                'contact_email': 'tanaka@active-sales.example.com',
                'contact_phone': '03-1000-0001',
            },
            {
                'name': 'マーケットリンクス株式会社',
                'industry': 'マーケティング・広告',
                'contact_person': '佐藤花子',
                'contact_email': 'sato@market-links.example.com',
                'contact_phone': '06-2000-0002',
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

        project, created = Project.objects.update_or_create(
            name='サンプル案件A',
            defaults={
                'client': next(iter(client_map.values())),
                'status': '進行中',
                'start_date': date.today(),
                'description': 'デモ用の案件です。',
            },
        )

        company = next(iter(company_map.values()))
        ProjectCompany.objects.update_or_create(
            project=project,
            company=company,
            defaults={'status': '未接触'},
        )

        self.stdout.write(
            f"  - project '{project.name}' prepared and linked with company '{company.name}'"
        )
