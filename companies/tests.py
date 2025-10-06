from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Company, Executive
from django.contrib.auth import get_user_model


class CompanyCSVImportTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.user)

    def _import_csv(self, content: str):
        file = SimpleUploadedFile(
            "companies.csv",
            content.encode("utf-8"),
            content_type="text/csv",
        )
        url = "/api/v1/companies/import_csv/"
        return self.client.post(url, {"file": file}, format="multipart")

    def test_import_csv_returns_detailed_error_information(self):
        csv_content = "name,employee_count\nTest Company,abc\n"
        response = self._import_csv(csv_content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)
        self.assertEqual(response.data["errors"][0]["row"], 2)
        self.assertEqual(response.data["errors"][0]["field"], "employee_count")
        self.assertEqual(response.data["errors"][0]["value"], "abc")

    def test_import_csv_creates_companies_when_valid(self):
        csv_content = (
            "name,industry,employee_count,revenue\n"
            "Valid Corp,IT,100,2000000\n"
        )

        response = self._import_csv(csv_content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["imported_count"], 1)
        self.assertTrue(Company.objects.filter(name="Valid Corp").exists())

    def test_import_csv_populates_extended_fields(self):
        csv_content = (
            "name,corporate_number,industry,contact_person_name,contact_person_position,facebook_url,"
            "tob_toc_type,business_description,prefecture,city,employee_count,revenue,capital,"
            "established_year,website_url,notes\n"
            "Advanced Corp,1234-5678-9012,IT,山田 太郎,CEO,https://www.facebook.com/example,toB,"
            "クラウド導入支援,東京都,渋谷区,50,1000000,5000000,2015,https://example.com/,アポ実績あり\n"
        )

        response = self._import_csv(csv_content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        company = Company.objects.get(name="Advanced Corp")
        self.assertEqual(company.corporate_number, "123456789012")
        self.assertEqual(company.contact_person_name, "山田 太郎")
        self.assertEqual(company.contact_person_position, "CEO")
        self.assertEqual(company.facebook_url, "https://www.facebook.com/example")
        self.assertEqual(company.tob_toc_type, "toB")
        self.assertEqual(company.business_description, "クラウド導入支援")
        self.assertEqual(company.prefecture, "東京都")
        self.assertEqual(company.city, "渋谷区")
        self.assertEqual(company.employee_count, 50)
        self.assertEqual(company.revenue, 1000000)
        self.assertEqual(company.capital, 5000000)
        self.assertEqual(company.established_year, 2015)
        self.assertEqual(company.website_url, "https://example.com/")
        self.assertEqual(company.notes, "アポ実績あり")
        self.assertEqual(response.data["executive_created_count"], 1)
        self.assertEqual(company.executives.count(), 1)
        executive = company.executives.first()
        self.assertEqual(executive.name, "山田 太郎")
        self.assertEqual(executive.position, "CEO")
        self.assertEqual(executive.facebook_url, "https://www.facebook.com/example")

    def test_import_csv_handles_multiple_executives_for_same_company(self):
        csv_content = (
            "name,corporate_number,contact_person_name,contact_person_position,facebook_url,prefecture,city\n"
            "Multi Exec Corp,1234567890123,佐藤 太郎,CEO,https://fb.com/taro,東京都,渋谷区\n"
            "Multi Exec Corp,1234567890123,鈴木 花子,COO,https://fb.com/hanako,東京都,渋谷区\n"
        )

        response = self._import_csv(csv_content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        company = Company.objects.get(name="Multi Exec Corp")
        self.assertEqual(response.data["imported_count"], 1)
        self.assertEqual(response.data["executive_created_count"], 2)
        self.assertEqual(company.executives.count(), 2)
        names = set(company.executives.values_list("name", flat=True))
        self.assertEqual(names, {"佐藤 太郎", "鈴木 花子"})


class CompanyViewSetBusinessTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.user)
        self.list_url = "/api/v1/companies/"

    def test_perform_create_normalizes_corporate_number(self):
        payload = {
            "name": "Normalize Corp",
            "corporate_number": "  123-456  ",
        }

        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        company = Company.objects.get(id=response.data["id"])
        self.assertEqual(company.corporate_number, "123456")

    def test_duplicate_corporate_number_raises_conflict(self):
        Company.objects.create(name="Existing Corp", corporate_number="9999999999999")
        payload = {
            "name": "Duplicate Corp",
            "corporate_number": "9999999999999",
        }

        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("message", response.data)

    def test_toggle_ng_action_flips_state(self):
        company = Company.objects.create(name="Toggle Corp")
        url = reverse("company-toggle-ng", args=[company.id])

        first_response = self.client.post(url, {"reason": "Need to block"}, format="json")
        company.refresh_from_db()

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertTrue(company.is_global_ng)
        self.assertEqual(first_response.data["reason"], "Need to block")

        second_response = self.client.post(url, {}, format="json")
        company.refresh_from_db()

        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertFalse(company.is_global_ng)

    def test_import_csv_requires_file(self):
        response = self.client.post("/api/v1/companies/import_csv/", {}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_import_csv_endpoint_creates_companies(self):
        csv_content = (
            "name,corporate_number,contact_person_name,contact_person_position,facebook_url,prefecture,city\n"
            "API Test Corp,1234567890123,山田 太郎,代表取締役,https://facebook.com/example,東京都,渋谷区\n"
        )
        file = SimpleUploadedFile(
            "companies.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post("/api/v1/companies/import_csv/", {"file": file}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("imported_count"), 1)
        company = Company.objects.get(name="API Test Corp")
        self.assertEqual(company.corporate_number, "1234567890123")
        self.assertEqual(company.contact_person_name, "山田 太郎")
        self.assertEqual(company.contact_person_position, "代表取締役")
        self.assertEqual(company.facebook_url, "https://facebook.com/example")
