from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from projects.models import ProjectSnapshot


class Command(BaseCommand):
    help = "指定日数より古い案件スナップショットを削除します"

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            help='保持期間（日数）をオーバーライドします。未指定の場合は設定値を使用します。'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='削除件数のみを表示し、削除は実行しません。'
        )

    def handle(self, *args, **options):
        retention_days = options.get('days') or getattr(settings, 'SNAPSHOT_RETENTION_DAYS', 7)
        dry_run = options.get('dry_run', False)

        cutoff = timezone.now() - timedelta(days=retention_days)
        queryset = ProjectSnapshot.objects.filter(created_at__lt=cutoff)
        count = queryset.count()

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[DRY-RUN] {count} 件のスナップショットが削除対象です（{retention_days}日超）。"
            ))
            return

        deleted_count, _ = queryset.delete()
        self.stdout.write(self.style.SUCCESS(
            f"{deleted_count} 件のスナップショットを削除しました（{retention_days}日超）。"
        ))
