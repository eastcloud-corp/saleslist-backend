from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Company
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
