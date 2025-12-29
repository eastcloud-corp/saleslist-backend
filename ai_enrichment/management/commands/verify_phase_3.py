"""
Phase 3-②/3-③ 検証用Django管理コマンド

使用方法:
    python manage.py verify_phase_3
"""
from django.core.management.base import BaseCommand
from django.db import connection
from companies.models import Company


class Command(BaseCommand):
    help = 'Phase 3-②/3-③の実装を検証する'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("Phase 3-②/3-③ 検証開始"))
        self.stdout.write("=" * 60)
        self.stdout.write("")

        # 1. マイグレーション確認
        self.stdout.write(self.style.WARNING("📋 Step 1: マイグレーション確認"))
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'companies' 
                  AND column_name = 'next_retry_strategy'
            """)
            result = cursor.fetchone()
            
            if result:
                self.stdout.write(self.style.SUCCESS(f"✅ next_retry_strategyフィールドが存在します"))
                self.stdout.write(f"   - データ型: {result[1]}")
                self.stdout.write(f"   - NULL許可: {result[2]}")
                self.stdout.write(f"   - 最大長: {result[3]}")
            else:
                self.stdout.write(self.style.ERROR("❌ next_retry_strategyフィールドが見つかりません"))
                self.stdout.write(self.style.WARNING("   マイグレーションを適用してください: python manage.py migrate"))
                return
        self.stdout.write("")

        # 2. データ統計
        self.stdout.write(self.style.WARNING("📋 Step 2: データ統計"))
        
        # no_data企業の統計
        failed_companies = Company.objects.filter(ai_last_enrichment_status='failed')
        failed_count = failed_companies.count()
        failed_with_strategy = failed_companies.exclude(next_retry_strategy__isnull=True).count()
        
        self.stdout.write(f"失敗企業数: {failed_count}")
        self.stdout.write(f"  - next_retry_strategyが設定されている: {failed_with_strategy}")
        self.stdout.write(f"  - next_retry_strategyがNULL: {failed_count - failed_with_strategy}")
        
        # 成功/部分成功企業の統計
        success_companies = Company.objects.filter(ai_last_enrichment_status__in=['success', 'partial'])
        success_count = success_companies.count()
        success_with_none = success_companies.filter(next_retry_strategy='none').count()
        
        self.stdout.write(f"成功/部分成功企業数: {success_count}")
        self.stdout.write(f"  - next_retry_strategy='none': {success_with_none}")
        self.stdout.write(f"  - next_retry_strategyがNULLまたは'none'以外: {success_count - success_with_none}")
        self.stdout.write("")

        # 3. next_retry_strategyの分布
        self.stdout.write(self.style.WARNING("📋 Step 3: next_retry_strategyの分布"))
        
        from django.db.models import Count
        strategy_dist = Company.objects.values('next_retry_strategy').annotate(
            count=Count('id')
        ).order_by('-count')
        
        for item in strategy_dist:
            strategy = item['next_retry_strategy'] or 'NULL'
            count = item['count']
            self.stdout.write(f"  {strategy}: {count}")
        self.stdout.write("")

        # 4. 最近の補完実行結果
        self.stdout.write(self.style.WARNING("📋 Step 4: 最近の補完実行結果（失敗企業）"))
        recent_failed = failed_companies.order_by('-ai_last_enriched_at')[:5]
        
        if recent_failed.exists():
            for company in recent_failed:
                self.stdout.write(f"  ID: {company.id}, 名前: {company.name}")
                self.stdout.write(f"    ステータス: {company.ai_last_enrichment_status}")
                self.stdout.write(f"    再探索戦略: {company.next_retry_strategy or 'NULL'}")
                self.stdout.write(f"    最終補完日時: {company.ai_last_enriched_at}")
                self.stdout.write("")
        else:
            self.stdout.write(self.style.WARNING("  最近の失敗企業が見つかりません"))
            self.stdout.write("  AI補完タスクを実行してから再度検証してください")
        self.stdout.write("")

        # 5. 検証結果サマリー
        self.stdout.write(self.style.WARNING("📋 Step 5: 検証結果サマリー"))
        
        all_ok = True
        
        # チェック1: マイグレーション適用済み
        if not result:
            all_ok = False
            self.stdout.write(self.style.ERROR("❌ マイグレーションが適用されていません"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ マイグレーション適用済み"))
        
        # チェック2: 失敗企業にnext_retry_strategyが設定されている
        if failed_count > 0 and failed_with_strategy == 0:
            all_ok = False
            self.stdout.write(self.style.ERROR("❌ 失敗企業にnext_retry_strategyが設定されていません"))
        elif failed_count > 0:
            self.stdout.write(self.style.SUCCESS(f"✅ 失敗企業の{failed_with_strategy}/{failed_count}にnext_retry_strategyが設定されています"))
        
        # チェック3: 成功企業が'none'にリセットされている
        if success_count > 0 and success_with_none < success_count * 0.8:  # 80%以上が'none'であることを期待
            all_ok = False
            self.stdout.write(self.style.ERROR(f"⚠️  成功企業の{success_with_none}/{success_count}のみが'none'にリセットされています"))
        elif success_count > 0:
            self.stdout.write(self.style.SUCCESS(f"✅ 成功企業の{success_with_none}/{success_count}が'none'にリセットされています"))
        
        self.stdout.write("")
        
        if all_ok:
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(self.style.SUCCESS("✅ 検証完了: すべてのチェックがパスしました"))
            self.stdout.write(self.style.SUCCESS("=" * 60))
        else:
            self.stdout.write(self.style.ERROR("=" * 60))
            self.stdout.write(self.style.ERROR("❌ 検証完了: 一部のチェックが失敗しました"))
            self.stdout.write(self.style.ERROR("=" * 60))
            self.stdout.write("")
            self.stdout.write("次のアクション:")
            self.stdout.write("1. AI補完タスクを実行してから再度検証")
            self.stdout.write("2. ログを確認して[AI_ENRICH][NO_DATA_CLASSIFIED]が出力されているか確認")
            self.stdout.write("3. PHASE_3_VERIFICATION_CHECKLIST.mdを参照して詳細確認")
