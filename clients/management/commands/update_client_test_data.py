"""
既存のクライアントデータに企業情報フィールドを追加するコマンド
"""
from django.core.management.base import BaseCommand
from clients.models import Client


class Command(BaseCommand):
    help = 'Update existing client records with company info fields'

    def handle(self, *args, **options):
        # 既存のクライアントデータを更新
        clients_data = [
            {
                'name': '株式会社アクティブセールス',
                'contact_person_position': '営業部長',
                'facebook_url': 'https://facebook.com/active-sales',
                'employee_count': 150,
                'revenue': 800_000_000,
                'prefecture': '東京都',
            },
            {
                'name': 'マーケットリンクス株式会社',
                'contact_person_position': 'マーケティング部長',
                'facebook_url': 'https://facebook.com/market-links',
                'employee_count': 80,
                'revenue': 450_000_000,
                'prefecture': '大阪府',
            },
            {
                'name': 'グロースファネル株式会社',
                'contact_person_position': '代表取締役',
                'facebook_url': 'https://facebook.com/growth-funnel',
                'employee_count': 45,
                'revenue': 280_000_000,
                'prefecture': '愛知県',
            },
            {
                'name': 'ネクストカスタマー株式会社',
                'contact_person_position': 'カスタマーサクセス部長',
                'facebook_url': 'https://facebook.com/next-customer',
                'employee_count': 120,
                'revenue': 650_000_000,
                'prefecture': '神奈川県',
            },
            {
                'name': '株式会社グロースパートナー',
                'contact_person_position': '営業部長',
                'facebook_url': 'https://facebook.com/growth-partner',
                'employee_count': 200,
                'revenue': 1_200_000_000,
                'prefecture': '東京都',
            },
            {
                'name': 'マーケットエクスパンション株式会社',
                'contact_person_position': 'マーケティング部長',
                'facebook_url': 'https://facebook.com/market-expansion',
                'employee_count': 95,
                'revenue': 520_000_000,
                'prefecture': '大阪府',
            },
            {
                'name': 'ビジネスソリューション株式会社',
                'contact_person_position': '代表取締役',
                'facebook_url': 'https://facebook.com/business-solution',
                'employee_count': 60,
                'revenue': 380_000_000,
                'prefecture': '東京都',
            },
        ]

        updated = 0
        for data in clients_data:
            name = data.pop('name')
            try:
                client = Client.objects.get(name=name)
                for field, value in data.items():
                    setattr(client, field, value)
                client.save()
                updated += 1
                self.stdout.write(f'  ✓ Updated: {name}')
            except Client.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  - Not found: {name}'))

        self.stdout.write(self.style.SUCCESS(f'\nUpdated {updated} client records.'))

