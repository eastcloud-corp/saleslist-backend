"""
success 済み企業も含め、TARGET_FIELDS で未取得の項目がある企業向けに AI 補完ジョブをキュー投入する。

例（1ジョブ・25件・offset 0）:
  python manage.py enqueue_ai_enrich_backfill --limit 25 --offset 0

例（success も対象にしつつ、クールダウン無視で 10 バッチ連続投入）:
  python manage.py enqueue_ai_enrich_backfill --batches 10 --limit 25

例（業界カラムのみ補完。プロンプトが短くなり取りこぼしが減ることがある）:
  python manage.py enqueue_ai_enrich_backfill --only-fields industry --batches 10 --limit 25

同時実行で API 上限やワーカー負荷が跳ねるため、バッチ数は環境に合わせて調整すること。
"""

from django.core.management.base import BaseCommand

from data_collection.services import enqueue_job


class Command(BaseCommand):
    help = (
        "ai.enrich を enqueue_job で投入する（include_successful_companies / bypass_cooldown 付き）。"
        "デプロイ後の業界バックフィルなどに使う。"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=25,
            help="1ジョブあたりの最大処理件数（デフォルト: 25）",
        )
        parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help="未取得フィールドあり企業の先頭からスキップする件数",
        )
        parser.add_argument(
            "--batches",
            type=int,
            default=1,
            help="連続投入するジョブ数（各ジョブの offset は limit ずつ加算）",
        )
        parser.add_argument(
            "--no-include-successful",
            action="store_true",
            help="既定の「success 企業も対象」をオフにする",
        )
        parser.add_argument(
            "--no-bypass-cooldown",
            action="store_true",
            help="既定の「クールダウン無視」をオフにする",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="投入せずオプション内容だけ表示",
        )
        parser.add_argument(
            "--only-fields",
            default="",
            help="カンマ区切りの内部フィールド名（例: industry）。指定時はその項目が空の企業に対してのみAI依頼する",
        )

    def handle(self, *args, **options):
        limit = max(1, int(options["limit"]))
        start_offset = max(0, int(options["offset"]))
        batches = max(1, int(options["batches"]))
        include_successful = not options["no_include_successful"]
        bypass_cooldown = not options["no_bypass_cooldown"]
        dry_run = options["dry_run"]
        only_raw = (options.get("only_fields") or "").strip()
        only_list = [x.strip() for x in only_raw.split(",") if x.strip()]

        self.stdout.write(
            f"limit={limit}, start_offset={start_offset}, batches={batches}, "
            f"include_successful_companies={include_successful}, bypass_cooldown={bypass_cooldown}, "
            f"only_fields={only_list or '(all missing)'}, dry_run={dry_run}"
        )

        for i in range(batches):
            offset = start_offset + i * limit
            job_options = {
                "limit": limit,
                "offset": offset,
                "include_successful_companies": include_successful,
                "bypass_cooldown": bypass_cooldown,
            }
            if only_list:
                job_options["only_fields"] = only_list
            if dry_run:
                self.stdout.write(f"  [dry-run] batch {i + 1}/{batches} options={job_options}")
                continue
            run, async_result = enqueue_job(job_name="ai.enrich", options=job_options)
            task_id = async_result.id if async_result else None
            self.stdout.write(
                self.style.SUCCESS(
                    f"batch {i + 1}/{batches}: enqueued execution_uuid={run.execution_uuid} task_id={task_id} offset={offset}"
                )
            )
