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

from masters.models import Industry, Status
from accounts.models import User

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
    
    print("✅ 初期データ投入が完了しました！")
