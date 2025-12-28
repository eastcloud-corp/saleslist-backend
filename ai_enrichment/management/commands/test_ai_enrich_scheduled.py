"""
Celery Beat相当のAI補完タスクを手動実行するコマンド
cron実行の擬似テスト用
"""
from django.core.management.base import BaseCommand
from ai_enrichment.tasks import run_ai_enrich_scheduled


class Command(BaseCommand):
    help = "Celery Beat相当のAI補完タスクを手動実行（cron相当の擬似テスト）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--async",
            action="store_true",
            help="非同期で実行（Celeryタスクとしてキューに投入）",
        )

    def handle(self, *args, **options):
        self.stdout.write("🚀 Celery Beat相当のAI補完タスクを実行中...")

        try:
            if options["async"]:
                # 非同期実行（Celeryタスクとして）
                result = run_ai_enrich_scheduled.delay()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ タスクをキューに投入しました (task_id: {result.id})"
                    )
                )
                self.stdout.write(
                    f"   実行状況は以下のコマンドで確認できます:"
                )
                self.stdout.write(
                    f"   docker compose -f saleslist-infra/docker-compose/dev/docker-compose-dev.yml logs -f worker"
                )
            else:
                # 同期実行（直接実行）
                result = run_ai_enrich_scheduled()
                self.stdout.write(
                    self.style.SUCCESS("✅ タスクの実行が完了しました")
                )
                self.stdout.write(f"   実行結果: {result}")

                # 実行結果の詳細を表示
                if isinstance(result, dict):
                    self.stdout.write(f"\n実行詳細:")
                    for key, value in result.items():
                        self.stdout.write(f"   {key}: {value}")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ エラーが発生しました: {e}")
            )
            import traceback

            traceback.print_exc()
            raise

