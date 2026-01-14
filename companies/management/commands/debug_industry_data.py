from django.core.management.base import BaseCommand
from companies.models import Company
from masters.models import Industry
from django.db.models import Q, Count


class Command(BaseCommand):
    help = '業界フィルター不具合調査: DBの内容を確認'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("業界フィルター不具合調査: DBの内容確認")
        self.stdout.write("=" * 80)
        
        # 1. マスターデータの確認
        self.stdout.write("\n【1. マスターデータの確認】")
        self.stdout.write("-" * 80)
        
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
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ 業界カテゴリ「{consulting_category.name}」が見つかりました (ID: {consulting_category.id})"
                )
            )
            # 子業界（業種）を取得
            sub_industries = Industry.objects.filter(
                parent_industry=consulting_category,
                is_active=True
            )
            sub_names = [sub.name for sub in sub_industries]
            self.stdout.write(f"  子業界（業種）数: {sub_industries.count()}")
            self.stdout.write(f"  子業界（業種）名: {sub_names}")
        else:
            self.stdout.write(
                self.style.ERROR("✗ 業界カテゴリ「コンサルティング・専門サービス」が見つかりませんでした")
            )
        
        if it_category:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ 業界カテゴリ「{it_category.name}」が見つかりました (ID: {it_category.id})"
                )
            )
            # 子業界（業種）を取得
            sub_industries = Industry.objects.filter(
                parent_industry=it_category,
                is_active=True
            )
            sub_names = [sub.name for sub in sub_industries]
            self.stdout.write(f"  子業界（業種）数: {sub_industries.count()}")
            self.stdout.write(f"  子業界（業種）名: {sub_names}")
        else:
            self.stdout.write(
                self.style.ERROR("✗ 業界カテゴリ「IT・マスコミ」が見つかりませんでした")
            )
        
        # 2. 実際のCompanyデータのindustry値の分布を確認
        self.stdout.write("\n【2. Companyデータのindustry値の分布】")
        self.stdout.write("-" * 80)
        
        # 全Company数
        total_companies = Company.objects.count()
        self.stdout.write(f"全企業数: {total_companies}")
        
        # industryが空でない企業数
        companies_with_industry = Company.objects.exclude(industry__isnull=True).exclude(industry="")
        companies_with_industry_count = companies_with_industry.count()
        self.stdout.write(f"industryが設定されている企業数: {companies_with_industry_count}")
        
        # 業界カテゴリ名で検索（現状のロジック）
        self.stdout.write("\n【3. 現状の検索ロジックでの結果】")
        self.stdout.write("-" * 80)
        
        # 「コンサルティング・専門サービス」で部分一致検索
        consulting_query = Company.objects.filter(industry__icontains="コンサルティング・専門サービス")
        consulting_count = consulting_query.count()
        self.stdout.write(f"「コンサルティング・専門サービス」で部分一致検索: {consulting_count}件")
        
        if consulting_count > 0:
            self.stdout.write("  該当企業のindustry値（最初の10件）:")
            for company in consulting_query[:10]:
                self.stdout.write(f"    - {company.name}: {company.industry}")
        
        # 「IT・マスコミ」で部分一致検索
        it_query = Company.objects.filter(industry__icontains="IT・マスコミ")
        it_count = it_query.count()
        self.stdout.write(f"\n「IT・マスコミ」で部分一致検索: {it_count}件")
        
        if it_count > 0:
            self.stdout.write("  該当企業のindustry値（最初の10件）:")
            for company in it_query[:10]:
                self.stdout.write(f"    - {company.name}: {company.industry}")
        
        # 4. 業種名で検索（正しい検索方法）
        self.stdout.write("\n【4. 業種名での検索結果（修正後のロジック）】")
        self.stdout.write("-" * 80)
        
        if consulting_category:
            sub_industries = Industry.objects.filter(
                parent_industry=consulting_category,
                is_active=True
            )
            if sub_industries.exists():
                # 子業界名で検索
                sub_industry_names = [sub.name for sub in sub_industries]
                self.stdout.write(f"子業界名: {sub_industry_names}")
                
                # OR条件で検索
                consulting_correct_query = Q()
                for sub_name in sub_industry_names:
                    consulting_correct_query |= Q(industry__icontains=sub_name)
                
                consulting_correct_count = Company.objects.filter(consulting_correct_query).count()
                self.stdout.write(
                    self.style.SUCCESS(f"子業界名で検索: {consulting_correct_count}件")
                )
                
                if consulting_correct_count > 0:
                    self.stdout.write("  該当企業のindustry値（最初の10件）:")
                    for company in Company.objects.filter(consulting_correct_query)[:10]:
                        self.stdout.write(f"    - {company.name}: {company.industry}")
                else:
                    self.stdout.write(
                        self.style.WARNING("  ⚠️ 子業界名で検索しても0件です。実際のデータを確認してください。")
                    )
        
        if it_category:
            sub_industries = Industry.objects.filter(
                parent_industry=it_category,
                is_active=True
            )
            if sub_industries.exists():
                # 子業界名で検索
                sub_industry_names = [sub.name for sub in sub_industries]
                self.stdout.write(f"\n子業界名: {sub_industry_names}")
                
                # OR条件で検索
                it_correct_query = Q()
                for sub_name in sub_industry_names:
                    it_correct_query |= Q(industry__icontains=sub_name)
                
                it_correct_count = Company.objects.filter(it_correct_query).count()
                self.stdout.write(
                    self.style.SUCCESS(f"子業界名で検索: {it_correct_count}件")
                )
                
                if it_correct_count > 0:
                    self.stdout.write("  該当企業のindustry値（最初の10件）:")
                    for company in Company.objects.filter(it_correct_query)[:10]:
                        self.stdout.write(f"    - {company.name}: {company.industry}")
                else:
                    self.stdout.write(
                        self.style.WARNING("  ⚠️ 子業界名で検索しても0件です。実際のデータを確認してください。")
                    )
        
        # 5. industry値のユニークな値の上位30件を表示
        self.stdout.write("\n【5. industry値の分布（上位30件）】")
        self.stdout.write("-" * 80)
        
        industry_distribution = (
            Company.objects
            .exclude(industry__isnull=True)
            .exclude(industry="")
            .values('industry')
            .annotate(count=Count('id'))
            .order_by('-count')[:30]
        )
        
        for item in industry_distribution:
            self.stdout.write(f"  {item['industry']}: {item['count']}件")
        
        # 6. 子業界名とのマッチング確認
        self.stdout.write("\n【6. 子業界名とのマッチング確認】")
        self.stdout.write("-" * 80)
        
        if consulting_category:
            sub_industries = Industry.objects.filter(
                parent_industry=consulting_category,
                is_active=True
            )
            for sub_industry in sub_industries:
                matching_companies = Company.objects.filter(industry__icontains=sub_industry.name)
                count = matching_companies.count()
                if count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ 「{sub_industry.name}」: {count}件")
                    )
                    # 最初の3件のindustry値を表示
                    for company in matching_companies[:3]:
                        self.stdout.write(f"      - {company.name}: industry='{company.industry}'")
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  ✗ 「{sub_industry.name}」: 0件")
                    )
        
        if it_category:
            sub_industries = Industry.objects.filter(
                parent_industry=it_category,
                is_active=True
            )
            for sub_industry in sub_industries:
                matching_companies = Company.objects.filter(industry__icontains=sub_industry.name)
                count = matching_companies.count()
                if count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ 「{sub_industry.name}」: {count}件")
                    )
                    # 最初の3件のindustry値を表示
                    for company in matching_companies[:3]:
                        self.stdout.write(f"      - {company.name}: industry='{company.industry}'")
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  ✗ 「{sub_industry.name}」: 0件")
                    )
        
        # 7. 結論
        self.stdout.write("\n【7. 調査結果のまとめ】")
        self.stdout.write("-" * 80)
        
        if consulting_category:
            sub_industries = Industry.objects.filter(
                parent_industry=consulting_category,
                is_active=True
            )
            if sub_industries.exists():
                sub_industry_names = [sub.name for sub in sub_industries]
                consulting_correct_query = Q()
                for sub_name in sub_industry_names:
                    consulting_correct_query |= Q(industry__icontains=sub_name)
                consulting_correct_count = Company.objects.filter(consulting_correct_query).count()
                
                if consulting_correct_count == 0:
                    self.stdout.write(
                        self.style.ERROR(
                            "✗ 「コンサルティング・専門サービス」の子業界名で検索しても0件です。"
                        )
                    )
                    self.stdout.write("  → 可能性:")
                    self.stdout.write("    1. 実際のデータに該当する業種名が保存されていない")
                    self.stdout.write("    2. 業種名の表記が異なる（例: 「経営コンサルティング」vs「経営コンサル」）")
                    self.stdout.write("    3. マスターデータと実際のデータの不一致")
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ 「コンサルティング・専門サービス」の子業界名で検索: {consulting_correct_count}件"
                        )
                    )
        
        if it_category:
            sub_industries = Industry.objects.filter(
                parent_industry=it_category,
                is_active=True
            )
            if sub_industries.exists():
                sub_industry_names = [sub.name for sub in sub_industries]
                it_correct_query = Q()
                for sub_name in sub_industry_names:
                    it_correct_query |= Q(industry__icontains=sub_name)
                it_correct_count = Company.objects.filter(it_correct_query).count()
                
                if it_correct_count == 0:
                    self.stdout.write(
                        self.style.ERROR("✗ 「IT・マスコミ」の子業界名で検索しても0件です。")
                    )
                    self.stdout.write("  → 可能性:")
                    self.stdout.write("    1. 実際のデータに該当する業種名が保存されていない")
                    self.stdout.write("    2. 業種名の表記が異なる")
                    self.stdout.write("    3. マスターデータと実際のデータの不一致")
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ 「IT・マスコミ」の子業界名で検索: {it_correct_count}件")
                    )
        
        self.stdout.write("\n" + "=" * 80)
