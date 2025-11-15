#!/usr/bin/env python3
"""
初期データ投入スクリプト
"""
import os
import sys
import django

# Django設定を読み込み
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saleslist_backend.settings')
django.setup()

from datetime import date, timedelta
from masters.models import Industry, Status, ProjectProgressStatus, ServiceType, MediaType
from accounts.models import User
from clients.models import Client
from companies.models import Company
from projects.models import Project, ProjectCompany

def seed_industries():
    """業界マスターデータを投入"""
    industries = [
        ("IT・ソフトウェア", 1),
        ("マーケティング・広告", 2),
        ("製造業", 3),
        ("人材・派遣", 4),
        ("金融・保険", 5),
        ("不動産", 6),
        ("小売・EC", 7),
        ("飲食・宿泊", 8),
        ("医療・介護", 9),
        ("教育・学習支援", 10),
        ("その他", 99),
    ]
    
    for name, order in industries:
        industry, created = Industry.objects.get_or_create(
            name=name,
            defaults={'display_order': order}
        )
        if created:
            print(f"✓ 業界 '{name}' を作成しました")
        else:
            print(f"- 業界 '{name}' は既に存在します")

def seed_statuses():
    """ステータスマスターデータを投入"""
    statuses = [
        # 営業ステータス
        ("未接触", "contact", 1, "#6B7280", "営業活動未実施の状態"),
        ("DM送信予定", "contact", 2, "#F59E0B", "DM送信準備中"),
        ("DM送信済み", "contact", 3, "#3B82F6", "DM送信完了"),
        ("返信あり", "contact", 4, "#8B5CF6", "相手から返信を受信"),
        ("アポ獲得", "contact", 5, "#10B981", "商談約束を取得"),
        ("成約", "contact", 6, "#059669", "契約成立"),
        ("NG", "contact", 7, "#DC2626", "対応不可・拒否"),
        
        # プロジェクトステータス
        ("進行中", "project", 1, "#3B82F6", "プロジェクト実行中"),
        ("完了", "project", 2, "#10B981", "プロジェクト完了"),
        ("中止", "project", 3, "#DC2626", "プロジェクト中止"),
        
        # 企業ステータス
        ("アクティブ", "company", 1, "#10B981", "営業対象として有効"),
        ("非アクティブ", "company", 2, "#6B7280", "営業対象外"),
    ]
    
    for name, category, order, color, description in statuses:
        status, created = Status.objects.get_or_create(
            name=name,
            category=category,
            defaults={
                'display_order': order,
                'color_code': color,
                'description': description
            }
        )
        if created:
            print(f"✓ ステータス '{name}' ({category}) を作成しました")
        else:
            print(f"- ステータス '{name}' ({category}) は既に存在します")

def ensure_user(
    email: str,
    *,
    username: str,
    name: str,
    role: str,
    password: str,
    is_staff: bool = False,
    is_superuser: bool = False,
):
    """指定のユーザーを作成（既存ならパスワード・属性を同期）"""
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': username,
            'name': name,
            'role': role,
            'is_active': True,
            'is_staff': is_staff,
            'is_superuser': is_superuser,
        },
    )

    updated_fields = []

    if created:
        print(f"✓ ユーザー '{email}' を新規作成しました")
    else:
        if user.name != name:
            user.name = name
            updated_fields.append('name')
        if user.role != role:
            user.role = role
            updated_fields.append('role')
        if not user.is_active:
            user.is_active = True
            updated_fields.append('is_active')
        if user.is_staff != is_staff:
            user.is_staff = is_staff
            updated_fields.append('is_staff')
        if user.is_superuser != is_superuser:
            user.is_superuser = is_superuser
            updated_fields.append('is_superuser')

    if not user.check_password(password):
        user.set_password(password)
        updated_fields.append('password')

    if created or updated_fields:
        user.save(update_fields=None if created else updated_fields)
        if created:
            print(f"  - パスワードを設定しました")
        else:
            print(f"  - {email} の属性を更新: {', '.join(updated_fields)}")
    else:
        print(f"- ユーザー '{email}' は既に最新です")


def create_default_users():
    """開発用の標準ユーザーと管理者ユーザーを用意"""
    test_email = os.getenv("TEST_USER_EMAIL", "user@example.com")
    test_password = os.getenv("TEST_USER_PASSWORD", "password123")
    test_name = os.getenv("TEST_USER_NAME", "山田太郎")

    admin_email = os.getenv("ADMIN_USER_EMAIL", "reviewer@example.com")
    admin_password = os.getenv("ADMIN_USER_PASSWORD", "password123")
    admin_name = os.getenv("ADMIN_USER_NAME", "レビュアー")

    ensure_user(
        test_email,
        username=test_email,
        name=test_name,
        role='user',
        password=test_password,
    )
    ensure_user(
        admin_email,
        username=admin_email,
        name=admin_name,
        role='admin',
        password=admin_password,
        is_staff=True,
        is_superuser=True,
    )


def seed_user_data():
    """user@example.comに紐づくseedデータを作成"""
    user_email = "user@example.com"
    
    # ユーザーの存在確認
    try:
        user = User.objects.get(email=user_email)
        print(f"✓ ユーザー '{user_email}' を確認しました")
    except User.DoesNotExist:
        print(f"⚠ ユーザー '{user_email}' が存在しません。先にユーザーを作成してください。")
        return
    
    # マスターデータの確認と作成
    print("📋 マスターデータを確認中...")
    
    # ProjectProgressStatus
    progress_statuses = ['未着手', '着手中', '進行中', '完了']
    progress_lookup = {}
    for status_name in progress_statuses:
        status, created = ProjectProgressStatus.objects.get_or_create(
            name=status_name,
            defaults={'display_order': len(progress_lookup), 'is_active': True}
        )
        progress_lookup[status_name] = status
        if created:
            print(f"  ✓ 進行状況 '{status_name}' を作成しました")
    
    # ServiceType
    service_types = ['コンサルティング', 'マーケティング支援', '営業代行', 'CRM導入']
    service_lookup = {}
    for service_name in service_types:
        service, created = ServiceType.objects.get_or_create(
            name=service_name,
            defaults={'display_order': len(service_lookup), 'is_active': True}
        )
        service_lookup[service_name] = service
        if created:
            print(f"  ✓ サービス '{service_name}' を作成しました")
    
    # MediaType
    media_types = ['Facebook', 'LinkedIn', 'Instagram', 'Twitter']
    media_lookup = {}
    for media_name in media_types:
        media, created = MediaType.objects.get_or_create(
            name=media_name,
            defaults={'display_order': len(media_lookup), 'is_active': True}
        )
        media_lookup[media_name] = media
        if created:
            print(f"  ✓ 媒体 '{media_name}' を作成しました")
    
    # 企業データの作成
    print("🏢 企業データを作成中...")
    company_samples = [
        {
            'name': '株式会社テックソリューション',
            'industry': 'IT・ソフトウェア',
            'employee_count': 150,
            'revenue': 800_000_000,
            'prefecture': '東京都',
            'city': '渋谷区',
            'website_url': 'https://tech-solution.example.com',
            'contact_email': 'info@tech-solution.example.com',
            'phone': '03-1234-5678',
        },
        {
            'name': 'デジタルマーケティング株式会社',
            'industry': 'マーケティング・広告',
            'employee_count': 80,
            'revenue': 350_000_000,
            'prefecture': '大阪府',
            'city': '大阪市',
            'website_url': 'https://digital-marketing.example.com',
            'contact_email': 'contact@digital-marketing.example.com',
            'phone': '06-2345-6789',
        },
        {
            'name': 'クラウドサービス合同会社',
            'industry': 'IT・ソフトウェア',
            'employee_count': 120,
            'revenue': 600_000_000,
            'prefecture': '神奈川県',
            'city': '横浜市',
            'website_url': 'https://cloud-service.example.com',
            'contact_email': 'hello@cloud-service.example.com',
            'phone': '045-3456-7890',
        },
        {
            'name': 'イノベーションコンサルティング',
            'industry': 'コンサルティング',
            'employee_count': 60,
            'revenue': 280_000_000,
            'prefecture': '東京都',
            'city': '港区',
            'website_url': 'https://innovation-consulting.example.com',
            'contact_email': 'info@innovation-consulting.example.com',
            'phone': '03-4567-8901',
        },
        {
            'name': 'データアナリティクス株式会社',
            'industry': 'IT・ソフトウェア',
            'employee_count': 95,
            'revenue': 420_000_000,
            'prefecture': '東京都',
            'city': '新宿区',
            'website_url': 'https://data-analytics.example.com',
            'contact_email': 'sales@data-analytics.example.com',
            'phone': '03-5678-9012',
        },
    ]
    
    company_map = {}
    created_companies = 0
    for data in company_samples:
        company, was_created = Company.objects.update_or_create(
            name=data['name'],
            defaults=data
        )
        company_map[data['name']] = company
        if was_created:
            created_companies += 1
            print(f"  ✓ 企業 '{data['name']}' を作成しました")
        else:
            print(f"  - 企業 '{data['name']}' は既に存在します")
    
    print(f"  📊 企業: {created_companies}件作成 / {len(company_samples)}件合計")
    
    # クライアントデータの作成
    print("👥 クライアントデータを作成中...")
    client_samples = [
        {
            'name': '株式会社グロースパートナー',
            'industry': 'IT・ソフトウェア',
            'contact_person': '佐藤一郎',
            'contact_person_position': '営業部長',
            'contact_email': 'sato@growth-partner.example.com',
            'contact_phone': '03-1111-2222',
            'facebook_url': 'https://facebook.com/growth-partner',
            'employee_count': 200,
            'revenue': 1_200_000_000,
            'prefecture': '東京都',
        },
        {
            'name': 'マーケットエクスパンション株式会社',
            'industry': 'マーケティング・広告',
            'contact_person': '鈴木花子',
            'contact_person_position': 'マーケティング部長',
            'contact_email': 'suzuki@market-expansion.example.com',
            'contact_phone': '06-2222-3333',
            'facebook_url': 'https://facebook.com/market-expansion',
            'employee_count': 95,
            'revenue': 520_000_000,
            'prefecture': '大阪府',
        },
        {
            'name': 'ビジネスソリューション株式会社',
            'industry': 'コンサルティング',
            'contact_person': '田中健',
            'contact_person_position': '代表取締役',
            'contact_email': 'tanaka@business-solution.example.com',
            'contact_phone': '03-3333-4444',
            'facebook_url': 'https://facebook.com/business-solution',
            'employee_count': 60,
            'revenue': 380_000_000,
            'prefecture': '東京都',
        },
    ]
    
    client_map = {}
    created_clients = 0
    for data in client_samples:
        client, was_created = Client.objects.update_or_create(
            name=data['name'],
            defaults=data
        )
        client_map[data['name']] = client
        if was_created:
            created_clients += 1
            print(f"  ✓ クライアント '{data['name']}' を作成しました")
        else:
            print(f"  - クライアント '{data['name']}' は既に存在します")
    
    print(f"  📊 クライアント: {created_clients}件作成 / {len(client_samples)}件合計")
    
    # プロジェクトデータの作成
    print("📁 プロジェクトデータを作成中...")
    today = date.today()
    project_samples = [
        {
            'name': 'DX推進支援プロジェクト',
            'client': '株式会社グロースパートナー',
            'status': '進行中',
            'progress_status': '進行中',
            'service_type': 'コンサルティング',
            'media_type': 'LinkedIn',
            'start_offset': -60,
            'description': '企業のDX推進を支援するコンサルティング案件です。',
            'appointment_count': 5,
            'reply_count': 3,
            'companies': ['株式会社テックソリューション', 'クラウドサービス合同会社'],
        },
        {
            'name': 'マーケティング自動化プロジェクト',
            'client': 'マーケットエクスパンション株式会社',
            'status': '進行中',
            'progress_status': '着手中',
            'service_type': 'マーケティング支援',
            'media_type': 'Facebook',
            'start_offset': -30,
            'description': 'マーケティング自動化ツールの導入と運用支援を行います。',
            'appointment_count': 3,
            'reply_count': 2,
            'companies': ['デジタルマーケティング株式会社', 'データアナリティクス株式会社'],
        },
        {
            'name': 'CRM導入支援',
            'client': 'ビジネスソリューション株式会社',
            'status': '進行中',
            'progress_status': '未着手',
            'service_type': 'CRM導入',
            'media_type': 'Twitter',
            'start_offset': -10,
            'description': 'CRMシステムの導入と営業プロセスの最適化を支援します。',
            'appointment_count': 2,
            'reply_count': 1,
            'companies': ['イノベーションコンサルティング'],
        },
    ]
    
    created_projects = 0
    created_project_companies = 0
    for sample in project_samples:
        client = client_map.get(sample['client'])
        if not client:
            print(f"  ⚠ クライアント '{sample['client']}' が見つかりません。スキップします。")
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
        
        if was_created:
            created_projects += 1
            print(f"  ✓ プロジェクト '{sample['name']}' を作成しました")
        else:
            print(f"  - プロジェクト '{sample['name']}' は既に存在します")
        
        # プロジェクト企業の作成
        for idx, company_name in enumerate(sample['companies'], start=1):
            company = company_map.get(company_name)
            if not company:
                continue
            
            status_map = {
                1: '未接触',
                2: 'DM送信予定',
                3: 'DM送信済み',
            }
            project_company, pc_created = ProjectCompany.objects.update_or_create(
                project=project,
                company=company,
                defaults={
                    'status': status_map.get(idx, '未接触'),
                    'is_active': True,
                },
            )
            if pc_created:
                created_project_companies += 1
    
    print(f"  📊 プロジェクト: {created_projects}件作成 / {len(project_samples)}件合計")
    print(f"  📊 プロジェクト企業: {created_project_companies}件作成")
    
    print(f"✅ user@example.com用のseedデータ作成が完了しました！")

if __name__ == '__main__':
    print("🌱 初期データ投入を開始します...")
    print()
    
    print("📊 業界マスターデータを投入中...")
    seed_industries()
    print()
    
    print("📋 ステータスマスターデータを投入中...")
    seed_statuses()
    print()
    
    print("👤 開発用ユーザーを作成中...")
    create_default_users()
    print()
    
    print("📦 user@example.com用のseedデータを作成中...")
    seed_user_data()
    print()
    
    print("✅ 初期データ投入が完了しました！")
