from statistics import mean
from time import perf_counter

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.test import Client


class Command(BaseCommand):
    help = "案件管理系APIのレスポンス時間を計測します。"

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, help="force_loginに使用するユーザーID")
        parser.add_argument("--iterations", type=int, default=3, help="各リクエストを実行する回数")
        parser.add_argument("--page", type=int, default=1, help="計測対象ページ番号")
        parser.add_argument(
            "--page-size", type=int, default=20, help="page-lock計測時に使用するページサイズ"
        )
        parser.add_argument(
            "--filter-hash", default="default", help="page-lock計測時に使用するfilter_hash"
        )
        parser.add_argument(
            "--management-mode",
            action="store_true",
            help="案件一覧取得時にmanagement_mode=trueを付与する",
        )
        parser.add_argument(
            "--access-token",
            default="",
            help="Bearerトークンを指定した場合はそれを利用して認証する",
        )

    def handle(self, *args, **options):
        user_id = options.get("user_id")
        iterations = options["iterations"]
        page = options["page"]
        page_size = options["page_size"]
        filter_hash = options["filter_hash"]
        management_mode = options["management_mode"]

        if iterations < 1:
            raise CommandError("iterations は1以上を指定してください")

        client = Client()
        access_token = options.get("access_token")
        if access_token:
            client.defaults['HTTP_AUTHORIZATION'] = f"Bearer {access_token}"
        elif user_id:
            user_model = get_user_model()
            try:
                user = user_model.objects.get(pk=user_id)
            except user_model.DoesNotExist as exc:
                raise CommandError(f"ユーザー(ID={user_id})が見つかりません") from exc
            client.force_login(user)
        else:
            raise CommandError("--access-token もしくは --user-id のいずれかを指定してください")

        list_path = "/api/v1/projects/"
        if management_mode:
            list_query = {"management_mode": "true", "page": page}
        else:
            list_query = {"page": page}

        self.stdout.write(self.style.NOTICE("[1] 案件一覧 API 計測"))
        list_durations = []
        for _ in range(iterations):
            started = perf_counter()
            response = client.get(list_path, list_query)
            elapsed = (perf_counter() - started) * 1000
            list_durations.append(elapsed)
            count_display = "n/a"
            if response.headers.get("Content-Type", "").startswith("application/json"):
                try:
                    payload = response.json()
                    count_display = payload.get("count", "n/a")
                except Exception:
                    count_display = "parse-error"
            self.stdout.write(
                f"  - status={response.status_code} duration={elapsed:.2f}ms count={count_display}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "  -> 平均 {:.2f}ms / 最大 {:.2f}ms".format(mean(list_durations), max(list_durations))
            )
        )

        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("[2] page-lock API 計測"))
        lock_path = "/api/v1/projects/page-lock/"
        lock_payload = {"page": page, "page_size": page_size, "filter_hash": filter_hash}
        release_url = f"{lock_path}?page={page}&filter_hash={filter_hash}"
        lock_durations = []

        for _ in range(iterations):
            started = perf_counter()
            response = client.post(lock_path, lock_payload, content_type="application/json")
            elapsed = (perf_counter() - started) * 1000
            lock_durations.append(elapsed)
            self.stdout.write(
                f"  - ACQUIRE status={response.status_code} duration={elapsed:.2f}ms"
            )
            # ロック取得に成功した場合は即座に解放しておく
            client.delete(release_url)

        self.stdout.write(
            self.style.SUCCESS(
                "  -> 平均 {:.2f}ms / 最大 {:.2f}ms".format(mean(lock_durations), max(lock_durations))
            )
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("計測が完了しました。"))
