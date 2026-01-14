#!/usr/bin/env python3
"""
業界フィルター不具合調査用スクリプト

使用方法:
    python manage.py shell < scripts/debug_industry_filter.py
    または
    python scripts/debug_industry_filter.py (Django設定済みの場合)
"""
import os
import sys
import django

# Django設定を読み込み
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saleslist_backend.settings')
    django.setup()

from companies.models import Company
from masters.models import Industry
from django.db.models import Q, Count

def debug_industry_filter():
    """業界フィルターの不具合を調査"""
    
    print("=" * 80)
    print("業界フィルター不具合調査")
    print("=" * 80)
    
    # 1. マスターデータの確認
    print("\n【1. マスターデータの確認】")
    print("-" * 80)
    
    # 業界カテゴリ（親業界）
    consulting_category = Industry.objects.filter(
        name="コンサルティング・専門サービス",
        is_category=True
    ).first()
    
    it_category = Industry.objects.filter(
        name="IT・マスコミ",
        is_category=True
    ).first()
    
    if consulting_category:
        print(f"✓ 業界カテゴリ「{consulting_category.name}」が見つかりました (ID: {consulting_category.id})")
        # 子業界（業種）を取得
        sub_industries = Industry.objects.filter(
            parent_industry=consulting_category,
            is_active=True
        )
        print(f"  子業界（業種）: {[sub.name for sub in sub_industries]}")
    else:
        print("✗ 業界カテゴリ「コンサルティング・専門サービス」が見つかりませんでした")
    
    if it_category:
        print(f"✓ 業界カテゴリ「{it_category.name}」が見つかりました (ID: {it_category.id})")
        # 子業界（業種）を取得
        sub_industries = Industry.objects.filter(
            parent_industry=it_category,
            is_active=True
        )
        print(f"  子業界（業種）: {[sub.name for sub in sub_industries]}")
    else:
        print("✗ 業界カテゴリ「IT・マスコミ」が見つかりませんでした")
    
    # 2. 実際のCompanyデータのindustry値の分布を確認
    print("\n【2. Companyデータのindustry値の分布】")
    print("-" * 80)
    
    # 全Company数
    total_companies = Company.objects.count()
    print(f"全企業数: {total_companies}")
    
    # industryが空でない企業数
    companies_with_industry = Company.objects.exclude(industry__isnull=True).exclude(industry="")
    companies_with_industry_count = companies_with_industry.count()
    print(f"industryが設定されている企業数: {companies_with_industry_count}")
    
    # 業界カテゴリ名で検索（現状のロジック）
    print("\n【3. 現状の検索ロジックでの結果】")
    print("-" * 80)
    
    # 「コンサルティング・専門サービス」で部分一致検索
    consulting_query = Company.objects.filter(industry__icontains="コンサルティング・専門サービス")
    consulting_count = consulting_query.count()
    print(f"「コンサルティング・専門サービス」で部分一致検索: {consulting_count}件")
    
    if consulting_count > 0:
        print("  該当企業のindustry値（最初の10件）:")
        for company in consulting_query[:10]:
            print(f"    - {company.name}: {company.industry}")
    
    # 「IT・マスコミ」で部分一致検索
    it_query = Company.objects.filter(industry__icontains="IT・マスコミ")
    it_count = it_query.count()
    print(f"\n「IT・マスコミ」で部分一致検索: {it_count}件")
    
    if it_count > 0:
        print("  該当企業のindustry値（最初の10件）:")
        for company in it_query[:10]:
            print(f"    - {company.name}: {company.industry}")
    
    # 4. 業種名で検索（正しい検索方法）
    print("\n【4. 業種名での検索結果（正しい検索方法）】")
    print("-" * 80)
    
    if consulting_category:
        sub_industries = Industry.objects.filter(
            parent_industry=consulting_category,
            is_active=True
        )
        if sub_industries.exists():
            # 子業界名で検索
            sub_industry_names = [sub.name for sub in sub_industries]
            print(f"子業界名: {sub_industry_names}")
            
            # OR条件で検索
            consulting_correct_query = Q()
            for sub_name in sub_industry_names:
                consulting_correct_query |= Q(industry__icontains=sub_name)
            
            consulting_correct_count = Company.objects.filter(consulting_correct_query).count()
            print(f"子業界名で検索: {consulting_correct_count}件")
            
            if consulting_correct_count > 0:
                print("  該当企業のindustry値（最初の10件）:")
                for company in Company.objects.filter(consulting_correct_query)[:10]:
                    print(f"    - {company.name}: {company.industry}")
    
    if it_category:
        sub_industries = Industry.objects.filter(
            parent_industry=it_category,
            is_active=True
        )
        if sub_industries.exists():
            # 子業界名で検索
            sub_industry_names = [sub.name for sub in sub_industries]
            print(f"\n子業界名: {sub_industry_names}")
            
            # OR条件で検索
            it_correct_query = Q()
            for sub_name in sub_industry_names:
                it_correct_query |= Q(industry__icontains=sub_name)
            
            it_correct_count = Company.objects.filter(it_correct_query).count()
            print(f"子業界名で検索: {it_correct_count}件")
            
            if it_correct_count > 0:
                print("  該当企業のindustry値（最初の10件）:")
                for company in Company.objects.filter(it_correct_query)[:10]:
                    print(f"    - {company.name}: {company.industry}")
    
    # 5. industry値のユニークな値の上位20件を表示
    print("\n【5. industry値の分布（上位20件）】")
    print("-" * 80)
    
    industry_distribution = (
        Company.objects
        .exclude(industry__isnull=True)
        .exclude(industry="")
        .values('industry')
        .annotate(count=Count('id'))
        .order_by('-count')[:20]
    )
    
    for item in industry_distribution:
        print(f"  {item['industry']}: {item['count']}件")
    
    # 6. 結論
    print("\n【6. 調査結果のまとめ】")
    print("-" * 80)
    
    if consulting_category and consulting_count == 0:
        print("✗ 「コンサルティング・専門サービス」で検索すると0件")
        print("  → 原因: Company.industryフィールドには業界カテゴリ名ではなく業種名が保存されている")
        print("  → 解決策: 業界カテゴリを選択した場合、そのカテゴリに紐づく業種名で検索する必要がある")
    
    if it_category and it_count == 0:
        print("✗ 「IT・マスコミ」で検索すると0件")
        print("  → 原因: Company.industryフィールドには業界カテゴリ名ではなく業種名が保存されている")
        print("  → 解決策: 業界カテゴリを選択した場合、そのカテゴリに紐づく業種名で検索する必要がある")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    debug_industry_filter()
