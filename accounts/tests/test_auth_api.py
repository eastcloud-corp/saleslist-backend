from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.cache import caches
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class AuthAPITests(APITestCase):
    def setUp(self):
        self.password = "Secret123!"
        self.user = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            name="管理者",
            role="admin",
            password=self.password,
        )

    def test_login_success_updates_last_login_and_returns_tokens(self):
        response = self.client.post(
            reverse("login"),
            {"email": self.user.email, "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login_at)
        self.assertTrue(timezone.now() - self.user.last_login_at < timezone.timedelta(minutes=1))

    def test_login_with_invalid_credentials_returns_400(self):
        response = self.client.post(
            reverse("login"),
            {"email": self.user.email, "password": "wrong"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_refresh_requires_token(self):
        response = self.client.post(reverse("token_refresh"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error"), "refresh_token が必要です")

    def test_refresh_returns_new_tokens(self):
        login_response = self.client.post(
            reverse("login"),
            {"email": self.user.email, "password": self.password},
            format="json",
        )
        refresh_token = login_response.data["refresh_token"]

        response = self.client.post(
            reverse("token_refresh"),
            {"refresh_token": refresh_token},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)

    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
    def test_login_rate_limit_blocks_after_threshold(self):
        caches['default'].clear()
        payload = {"email": self.user.email, "password": "wrong"}

        for _ in range(10):
            response = self.client.post(reverse("login"), payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(reverse("login"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_logout_succeeds_even_with_invalid_refresh_token(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("logout"),
            {"refresh_token": "invalid-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("message"), "ログアウトしました")
        self.client.force_authenticate(user=None)

    def test_me_view_returns_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)
        self.client.force_authenticate(user=None)

    def test_create_user_view_creates_user(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "email": "new_user@example.com",
            "name": "新規ユーザー",
            "password": "Pass12345!",
            "role": "user",
        }
        response = self.client.post(reverse("create_user"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = User.objects.get(email=payload["email"])
        self.assertEqual(created.name, payload["name"])
        self.client.force_authenticate(user=None)

    def test_users_list_returns_count_and_results(self):
        another_user = User.objects.create_user(
            username="member@example.com",
            email="member@example.com",
            name="メンバー",
            role="user",
            password="Member123!",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("users_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 2)
        emails = {item["email"] for item in response.data["results"]}
        self.assertIn(another_user.email, emails)
        self.client.force_authenticate(user=None)

    def test_update_user_view_updates_fields(self):
        target = User.objects.create_user(
            username="target@example.com",
            email="target@example.com",
            name="ターゲット",
            role="user",
            password="Target123!",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse("update_user", args=[target.id]),
            {"name": "更新済み", "is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        target.refresh_from_db()
        self.assertEqual(target.name, "更新済み")
        self.assertFalse(target.is_active)
        self.client.force_authenticate(user=None)

    def test_update_user_returns_404_for_missing_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse("update_user", args=[9999]),
            {"name": "not-found"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data.get("error"), "ユーザーが見つかりません")
        self.client.force_authenticate(user=None)
