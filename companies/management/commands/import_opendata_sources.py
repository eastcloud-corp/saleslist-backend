from __future__ import annotations

import logging
from typing import List, Optional, Sequence

from django.core.management.base import BaseCommand

from companies.services.opendata_sources import ingest_opendata_sources, load_opendata_configs

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "自治体オープンデータ等のルールベース候補を取得し、レビュー候補として投入します。"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--source",
            action="append",
            dest="source_keys",
            help="対象とするソースキー。複数指定可。未指定時は全ソースが対象。",
        )
        parser.add_argument(
            "--limit",
            type=int,
            dest="limit",
            help="各ソースから処理する行数の上限。",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="候補を投入せず統計のみ出力します。",
        )

    def handle(self, *args, **options):
        configs = load_opendata_configs()
        if not configs:
            self.stdout.write(self.style.WARNING("利用可能なオープンデータの設定が見つかりません。"))
            return

        result = ingest_opendata_sources(
            source_keys=options.get("source_keys"),
            limit=options.get("limit"),
            dry_run=options.get("dry_run", False),
            config_map=configs,
        )

        summary = (
            "オープンデータ取り込み完了: "
            f"sources={result.get('processed_sources', 0)} "
            f"rows={result.get('rows', 0)} "
            f"matched={result.get('matched', 0)} "
            f"created={result.get('created', 0)}"
        )
        self.stdout.write(self.style.SUCCESS(summary))
        if result.get("dry_run"):
            self.stdout.write(self.style.WARNING("dry-run のため候補は投入していません。"))
