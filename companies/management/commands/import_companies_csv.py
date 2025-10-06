from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from companies.importers import import_companies_csv


class Command(BaseCommand):
    help = "CSVファイルから企業・担当者情報を取り込む"

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='インポート対象のCSVファイルパス')

    def handle(self, *args, **options):
        csv_path = Path(options['csv_path']).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f'指定されたファイルが見つかりません: {csv_path}')

        self.stdout.write(self.style.NOTICE(f'CSVインポート開始: {csv_path}'))
        with csv_path.open('rb') as file_obj:
            result, error_payload = import_companies_csv(file_obj)

        if error_payload:
            self.stderr.write(self.style.ERROR(error_payload.get('error', 'インポート中にエラーが発生しました')))
            errors = error_payload.get('errors')
            if errors:
                for err in errors[:10]:
                    self.stderr.write(f"  行{err.get('row')}: {err.get('field')} -> {err.get('message')} (値: {err.get('value')})")
                if len(errors) > 10:
                    self.stderr.write(f"  ...ほか {len(errors) - 10} 件")
            raise CommandError('CSVインポートに失敗しました')

        message = result.get('message', 'インポートが完了しました')
        self.stdout.write(self.style.SUCCESS(message))
        self.stdout.write(f"  新規登録: {result.get('imported_count')} 件")
        self.stdout.write(f"  更新: {result.get('company_updated_count')} 件")
        self.stdout.write(f"  役員追加: {result.get('executive_created_count')} 件 / 更新: {result.get('executive_updated_count')} 件")
        self.stdout.write(f"  法人番号未入力: {result.get('missing_corporate_number_count')} 件")
