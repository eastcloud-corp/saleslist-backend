from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from companies.models import Company


class CompanyCreationTests(APITestCase):
    def setUp(self):
        self.base_url = "/api/v1/companies/"
        User = get_user_model()
        self.user = User.objects.create_user(username="tester", password="password", email="tester@example.com")
        self.client.force_authenticate(user=self.user)

    def test_create_company_with_unique_corporate_number(self):
        payload = {
            "name": "テスト企業A",
            "corporate_number": "1234567890123",
            "industry": "IT",
        }

        response = self.client.post(self.base_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], payload["name"])
        self.assertEqual(response.data["corporate_number"], payload["corporate_number"])

    def test_create_company_duplicate_corporate_number_returns_conflict(self):
        Company.objects.create(name="既存企業", corporate_number="1234567890123")

        payload = {
            "name": "重複企業",
            "corporate_number": "1234567890123",
            "industry": "IT",
        }

        response = self.client.post(self.base_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("message", response.data)
        self.assertIn("duplicate_with", response.data)
        self.assertEqual(Company.objects.filter(corporate_number="1234567890123").count(), 1)


class CompanyCSVImportTests(APITestCase):
    def setUp(self):
        self.import_url = "/api/v1/companies/import_csv/"
        User = get_user_model()
        self.user = User.objects.create_user(username="importer", password="password", email="importer@example.com")
        self.client.force_authenticate(user=self.user)
        Company.objects.create(name="既存企業", corporate_number="9999999999999")

    def _build_csv_file(self, content: str) -> SimpleUploadedFile:
        return SimpleUploadedFile(
            "companies.csv",
            content.encode("utf-8"),
            content_type="text/csv",
        )

    def test_import_csv_skips_and_reports_duplicates(self):
        csv_rows = """Company Name,Corporate Number,Industry,Employee Count,Revenue,Location,Website,Phone,Email,Description,Status
ユニーク株式会社,1234567890123,Technology,50,1000000,Tokyo,https://unique.example.com,03-0000-0000,unique@example.com,Unique row,active
既存重複株式会社,9999999999999,Finance,20,500000,Osaka,https://dup-existing.example.com,06-0000-0000,dup-existing@example.com,Duplicate existing,active
CSV内重複株式会社,1234567890123,Technology,50,1000000,Tokyo,https://dup-internal.example.com,03-0000-0001,dup-internal@example.com,Duplicate inside CSV,active
"""
        uploaded = self._build_csv_file(csv_rows)

        response = self.client.post(self.import_url, {"file": uploaded}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["imported_count"], 1)
        self.assertEqual(response.data["duplicate_count"], 2)
        self.assertEqual(response.data["missing_corporate_number_count"], 0)
        self.assertEqual(len(response.data["duplicates"]), 2)

        self.assertTrue(Company.objects.filter(name="ユニーク株式会社").exists())
        self.assertFalse(Company.objects.filter(name="既存重複株式会社").exists())
        self.assertEqual(Company.objects.filter(corporate_number="1234567890123").count(), 1)
