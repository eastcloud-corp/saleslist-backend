from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.core.management import call_command, CommandError
from django.urls import reverse
from django.test import override_settings, SimpleTestCase, TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from .models import (
    Company,
    Executive,
    CompanyReviewBatch,
    CompanyReviewItem,
    CompanyUpdateCandidate,
    ExternalSourceRecord,
)
from .services.review_ingestion import create_candidate_entry, ingest_rule_based_candidates
from .services.corporate_number_client import (
    CorporateNumberAPIClient,
    CorporateNumberAPIError,
    select_best_match,
)
from .management.commands.import_corporate_numbers import run_corporate_number_import
from .services.opendata_sources import OpenDataSourceConfig, ingest_opendata_sources
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

    def test_industry_filter_supports_partial_match(self):
        Company.objects.create(name="複合業界社", industry="マーケティング・IT、不動産")
        Company.objects.create(name="製造業社", industry="製造業")

        response = self.client.get(f"{self.list_url}?industry=不動産")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertTrue(any(company["name"] == "複合業界社" for company in results))
        self.assertFalse(any(company["name"] == "製造業社" for company in results))


class CompanyReviewDecisionAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="reviewer",
            email="reviewer@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.user)

        self.company = Company.objects.create(
            name="Alpha Technologies",
            corporate_number="1234567890123",
            website_url="https://alpha.example.com",
        )
        self.batch = CompanyReviewBatch.objects.create(company=self.company)

        self.candidate = create_candidate_entry(
            company=self.company,
            field="website_url",
            candidate_value="https://alpha-tech.example.com",
            source_detail="unittest",
        )
        assert self.candidate is not None

        self.item = CompanyReviewItem.objects.create(
            batch=self.batch,
            candidate=self.candidate,
            field="website_url",
            current_value=self.company.website_url,
            candidate_value=self.candidate.candidate_value,
            confidence=self.candidate.confidence,
        )

    def _decide(self, payload):
        url = f"/api/v1/companies/reviews/{self.batch.id}/decide/"
        return self.client.post(url, payload, format="json")

    def test_reject_with_block_updates_candidate(self):
        payload = {
            "items": [
                {
                    "id": self.item.id,
                    "decision": "reject",
                    "comment": "同名別会社",
                    "block_reproposal": True,
                    "rejection_reason_code": CompanyUpdateCandidate.REJECTION_REASON_MISMATCH,
                    "rejection_reason_detail": "法人番号が一致しません",
                }
            ]
        }

        response = self._decide(payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.candidate.refresh_from_db()
        self.item.refresh_from_db()

        self.assertEqual(self.candidate.status, CompanyUpdateCandidate.STATUS_REJECTED)
        self.assertTrue(self.candidate.block_reproposal)
        self.assertEqual(
            self.candidate.rejection_reason_code,
            CompanyUpdateCandidate.REJECTION_REASON_MISMATCH,
        )
        self.assertEqual(self.candidate.rejection_reason_detail, "法人番号が一致しません")
        self.assertTrue(self.candidate.value_hash)
        self.assertEqual(self.item.decision, CompanyReviewItem.DECISION_REJECTED)

    def test_blocked_candidate_is_not_recreated(self):
        reject_payload = {
            "items": [
                {
                    "id": self.item.id,
                    "decision": "reject",
                    "block_reproposal": True,
                    "rejection_reason_code": CompanyUpdateCandidate.REJECTION_REASON_MISMATCH,
                }
            ]
        }
        reject_response = self._decide(reject_payload)
        self.assertEqual(reject_response.status_code, status.HTTP_200_OK)

        blocked = create_candidate_entry(
            company=self.company,
            field="website_url",
            candidate_value=self.candidate.candidate_value,
            source_detail="duplicate-test",
        )

        self.assertIsNone(blocked)

    def test_update_normalizes_numeric_fields(self):
        capital_candidate = create_candidate_entry(
            company=self.company,
            field="capital",
            candidate_value="6500000",
            source_type=CompanyUpdateCandidate.SOURCE_AI,
            source_detail="ai-test",
        )
        established_candidate = create_candidate_entry(
            company=self.company,
            field="established_year",
            candidate_value="2024",
            source_type=CompanyUpdateCandidate.SOURCE_AI,
            source_detail="ai-test",
        )
        self.assertIsNotNone(capital_candidate)
        self.assertIsNotNone(established_candidate)

        capital_item = CompanyReviewItem.objects.create(
            batch=self.batch,
            candidate=capital_candidate,
            field="capital",
            current_value="",
            candidate_value=capital_candidate.candidate_value,
            confidence=capital_candidate.confidence,
        )
        established_item = CompanyReviewItem.objects.create(
            batch=self.batch,
            candidate=established_candidate,
            field="established_year",
            current_value="",
            candidate_value=established_candidate.candidate_value,
            confidence=established_candidate.confidence,
        )

        payload = {
            "items": [
                {
                    "id": capital_item.id,
                    "decision": "update",
                    "new_value": "6,500,000円",
                },
                {
                    "id": established_item.id,
                    "decision": "update",
                    "new_value": "2024年",
                },
            ]
        }

        response = self._decide(payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.company.refresh_from_db()
        capital_item.refresh_from_db()
        established_item.refresh_from_db()

        self.assertEqual(self.company.capital, 6500000)
        self.assertEqual(self.company.established_year, 2024)
        self.assertEqual(capital_item.candidate_value, "6500000")
        self.assertEqual(established_item.candidate_value, "2024")

    def test_list_filter_by_field(self):
        from companies.services.review_ingestion import ingest_corporate_number_candidates

        ingest_corporate_number_candidates(
            [
                {
                    "company_id": self.company.id,
                    "corporate_number": "5555-6666-7777",
                }
            ]
        )

        response = self.client.get("/api/v1/companies/reviews/?field=corporate_number")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data.get("results", []) if isinstance(response.data, dict) else response.data
        self.assertTrue(len(results) >= 1)

        for batch in results:
            detail = self.client.get(f"/api/v1/companies/reviews/{batch['id']}/")
            self.assertEqual(detail.status_code, status.HTTP_200_OK)
            self.assertTrue(
                any(item["field"] == "corporate_number" for item in detail.data.get("items", []))
            )

    def test_retrieve_includes_completed_batches(self):
        self.batch.status = CompanyReviewBatch.STATUS_REJECTED
        self.batch.save(update_fields=["status"])

        response = self.client.get(f"/api/v1/companies/reviews/{self.batch.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_decide_returns_conflict_if_batch_completed(self):
        self.batch.status = CompanyReviewBatch.STATUS_REJECTED
        self.batch.save(update_fields=["status"])
        payload = {
            "items": [
                {
                    "id": self.item.id,
                    "decision": "approve",
                }
            ]
        }

        response = self._decide(payload)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data.get("status"), "conflict")

    @override_settings(DEBUG=False, ENABLE_REVIEW_SAMPLE_API=False)
    def test_generate_sample_forbidden_without_flag(self):
        response = self.client.post("/api/v1/companies/reviews/generate-sample/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(DEBUG=False, ENABLE_REVIEW_SAMPLE_API=True)
    def test_generate_sample_allowed_with_feature_flag(self):
        response = self.client.post("/api/v1/companies/reviews/generate-sample/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("created_count", response.data)


class CorporateNumberImportAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="importer",
            email="importer@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.user)

        self.company = Company.objects.create(
            name="法人番号テスト株式会社",
            prefecture="東京都",
            city="千代田区",
        )

    def _import(self, entries):
        url = "/api/v1/companies/reviews/import-corporate-numbers/"
        return self.client.post(url, {"entries": entries}, format="json")

    def test_import_corporate_number_creates_candidate(self):
        payload = [
            {
                "company_id": self.company.id,
                "corporate_number": "1234-5678-9012",
                "source_detail": "test-source",
            }
        ]

        response = self._import(payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get("created_count"), 1)

        candidate = CompanyUpdateCandidate.objects.get(company=self.company, field="corporate_number")
        self.assertEqual(candidate.candidate_value, "123456789012")
        self.assertEqual(candidate.source_detail, "test-source")
        self.assertEqual(candidate.confidence, 100)

        review_item = CompanyReviewItem.objects.get(candidate=candidate)
        self.assertEqual(review_item.candidate_value, "123456789012")

    @override_settings(DEBUG=False)
    def test_run_corporate_number_import_forbidden_on_non_debug(self):
        response = self.client.post(
            "/api/v1/companies/reviews/run-corporate-number-import/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(DEBUG=True)
@mock.patch("companies.views.run_corporate_number_import_task.apply_async")
def test_run_corporate_number_import_returns_result(self, mock_apply_async):
    mock_async = mock.Mock()
    mock_async.get.return_value = {
        "stats": {
            "checked": 1,
            "matched": 1,
            "not_found": 0,
            "errors": 0,
            "skipped_prefecture": 0,
            "skipped_name": 0,
            "skipped_cooldown": 0,
            "skipped_rate_limit": 0,
        },
        "entries_count": 1,
        "created_count": 1,
        "batch_ids": [42],
        "dry_run": False,
        "summary": "法人番号取得 完了: checked=1 matched=1 not_found=0 errors=0 skipped_prefecture=0 skipped_name=0 created=1",
        "skipped": False,
        "force_refresh": False,
        "daily_rate_limit_reached": False,
    }
    mock_apply_async.return_value = mock_async

    response = self.client.post(
        "/api/v1/companies/reviews/run-corporate-number-import/",
        {"limit": 10, "prefecture_strict": True},
        format="json",
    )

    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    mock_apply_async.assert_called_once()
    payload = mock_apply_async.call_args.kwargs.get("kwargs", {}).get("payload", {})
    self.assertEqual(payload.get("limit"), 10)
    self.assertTrue(payload.get("prefecture_strict"))
    self.assertFalse(payload.get("dry_run"))
    self.assertFalse(payload.get("force_refresh"))
    self.assertTrue(payload.get("allow_missing_token"))
    self.assertEqual(response.data["created_count"], 1)
    self.assertEqual(response.data["batch_ids"], [42])


@override_settings(DEBUG=True)
@mock.patch("companies.views.run_corporate_number_import_task.apply_async")
def test_run_corporate_number_import_dry_run_returns_200(self, mock_apply_async):
    mock_async = mock.Mock()
    mock_async.get.return_value = {
        "stats": {key: 0 for key in ["checked", "matched", "not_found", "errors", "skipped_prefecture", "skipped_name", "skipped_cooldown", "skipped_rate_limit"]},
        "entries_count": 0,
        "created_count": 0,
        "batch_ids": [],
        "dry_run": True,
        "summary": "dry-run",
        "skipped": False,
        "force_refresh": False,
        "daily_rate_limit_reached": False,
    }
    mock_apply_async.return_value = mock_async

    response = self.client.post(
        "/api/v1/companies/reviews/run-corporate-number-import/",
        {"dry_run": True},
        format="json",
    )

    self.assertEqual(response.status_code, status.HTTP_200_OK)
    mock_apply_async.assert_called_once()
    payload = mock_apply_async.call_args.kwargs.get("kwargs", {}).get("payload", {})
    self.assertTrue(payload.get("dry_run"))
    self.assertFalse(payload.get("prefecture_strict"))
    self.assertFalse(payload.get("force_refresh"))
    self.assertTrue(payload.get("allow_missing_token"))


@override_settings(DEBUG=True, CORPORATE_NUMBER_API_TOKEN="")
@mock.patch("companies.views.run_corporate_number_import_task.apply_async")
def test_run_corporate_number_import_skips_when_token_missing(self, mock_apply_async):
    mock_async = mock.Mock()
    mock_async.get.return_value = {
        "stats": {key: 0 for key in ["checked", "matched", "not_found", "errors", "skipped_prefecture", "skipped_name", "skipped_cooldown", "skipped_rate_limit"]},
        "entries_count": 0,
        "created_count": 0,
        "batch_ids": [],
        "dry_run": False,
        "summary": "法人番号APIトークンが未設定のため処理をスキップしました。",
        "skipped": True,
        "force_refresh": True,
        "daily_rate_limit_reached": False,
    }
    mock_apply_async.return_value = mock_async

    response = self.client.post(
        "/api/v1/companies/reviews/run-corporate-number-import/",
        {"force": True},
        format="json",
    )

    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertTrue(response.data.get("skipped"))
    self.assertEqual(response.data.get("created_count"), 0)
    payload = mock_apply_async.call_args.kwargs.get("kwargs", {}).get("payload", {})
    self.assertTrue(payload.get("force_refresh"))
    self.assertTrue(payload.get("allow_missing_token"))

    def test_duplicate_import_is_ignored(self):
        payload = [
            {
                "company_id": self.company.id,
                "corporate_number": "1234-5678-9012",
            }
        ]

        first = self._import(payload)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first.data.get("created_count"), 1)

        second = self._import(payload)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.data.get("created_count"), 0)


class RuleBasedIngestionTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Rule Based 株式会社",
            website_url="https://example.com",
            business_description="旧説明",
        )

    def test_ingest_rule_based_candidates_creates_review_item(self):
        entries = [
            {
                "company_id": self.company.id,
                "field": "business_description",
                "value": "AIソリューションとDX支援を提供",
                "source_detail": "gbizinfo",
                "source": "gbizinfo",
            }
        ]

        created = ingest_rule_based_candidates(entries)
        self.assertEqual(len(created), 1)
        item = created[0]
        self.assertEqual(item.field, "business_description")
        self.assertEqual(item.candidate_value, "AIソリューションとDX支援を提供")
        self.assertEqual(item.batch.company, self.company)
        self.assertEqual(item.batch.status, CompanyReviewBatch.STATUS_PENDING)

        record = ExternalSourceRecord.objects.get(company=self.company, field="business_description", source="gbizinfo")
        self.assertEqual(record.data_hash, CompanyUpdateCandidate.make_value_hash("business_description", "AIソリューションとDX支援を提供"))

    def test_ingest_rule_based_candidates_respects_cooldown(self):
        entries = [
            {
                "company_id": self.company.id,
                "field": "business_description",
                "value": "AIソリューションとDX支援を提供",
                "source": "gbizinfo",
            }
        ]

        ingest_rule_based_candidates(entries)
        record = ExternalSourceRecord.objects.get(company=self.company, field="business_description", source="gbizinfo")
        first_fetched = record.last_fetched_at

        ingest_rule_based_candidates(entries)
        record.refresh_from_db()
        self.assertEqual(CompanyReviewItem.objects.filter(batch__company=self.company, field="business_description").count(), 1)
        self.assertGreaterEqual(record.last_fetched_at, first_fetched)

    def test_ingest_rule_based_candidates_skips_when_current_value_matches(self):
        self.company.business_description = "既存説明"
        self.company.save(update_fields=["business_description"])

        entries = [
            {
                "company_id": self.company.id,
                "field": "business_description",
                "value": "既存説明",
                "source": "gbizinfo",
            }
        ]

        created = ingest_rule_based_candidates(entries)
        self.assertEqual(len(created), 0)
        record = ExternalSourceRecord.objects.get(company=self.company, field="business_description", source="gbizinfo")
        self.assertIsNotNone(record.last_fetched_at)

    def test_ingest_rule_based_candidates_allows_new_value_within_cooldown(self):
        base_entry = {
            "company_id": self.company.id,
            "field": "business_description",
            "source": "gbizinfo",
        }

        ingest_rule_based_candidates([{**base_entry, "value": "AIソリューションとDX支援を提供"}])

        ingest_rule_based_candidates([{**base_entry, "value": "クラウド導入支援"}])

        items = CompanyReviewItem.objects.filter(batch__company=self.company, field="business_description")
        self.assertEqual(items.count(), 2)
        record = ExternalSourceRecord.objects.get(company=self.company, field="business_description", source="gbizinfo")
        self.assertEqual(record.data_hash, CompanyUpdateCandidate.make_value_hash("business_description", "クラウド導入支援"))


class AIIngestionPlaceholderTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="ai-user",
            email="ai-user@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.user)

    @mock.patch("companies.views.run_ai_ingestion_stub.delay")
    def test_run_ai_ingestion_dispatches_task(self, mock_delay):
        mock_task = mock.Mock()
        mock_task.id = "task-123"
        mock_delay.return_value = mock_task

        payload = {"company_ids": [1, 2], "fields": ["business_description"], "prompt": "最新の事業内容を取得"}

        response = self.client.post(
            "/api/v1/companies/reviews/run-ai-ingestion/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_delay.assert_called_once_with(
            {
                "company_ids": [1, 2],
                "fields": ["business_description"],
                "prompt": "最新の事業内容を取得",
            }
        )
        self.assertEqual(response.data["status"], "accepted")
        self.assertEqual(response.data["task_id"], "task-123")

    def test_run_ai_ingestion_requires_fields_or_company_ids(self):
        response = self.client.post(
            "/api/v1/companies/reviews/run-ai-ingestion/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

@override_settings(DEBUG=True)
class OpenDataIngestionTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="opendata-user",
            email="opendata-user@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.user)


@mock.patch("companies.views.run_opendata_ingestion_task.apply_async")
def test_run_opendata_ingestion_returns_created(self, mock_apply_async):
    mock_async = mock.Mock()
    mock_async.get.return_value = {
        "processed_sources": 2,
        "rows": 120,
        "matched": 45,
        "created": 12,
        "dry_run": False,
    }
    mock_apply_async.return_value = mock_async

    response = self.client.post(
        "/api/v1/companies/reviews/run-opendata-ingestion/",
        {"sources": ["tokyo_corporate_members", "osaka_sm_support"], "limit": 200},
        format="json",
    )

    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    mock_apply_async.assert_called_once()
    payload = mock_apply_async.call_args.kwargs.get("kwargs", {}).get("payload", {})
    self.assertEqual(payload.get("source_keys"), ["tokyo_corporate_members", "osaka_sm_support"])
    self.assertEqual(payload.get("limit"), 200)
    self.assertFalse(payload.get("dry_run"))
    self.assertEqual(response.data["created"], 12)
    self.assertEqual(response.data["processed_sources"], 2)

@mock.patch("companies.views.run_opendata_ingestion_task.apply_async")
def test_run_opendata_ingestion_dry_run_returns_200(self, mock_apply_async):
    mock_async = mock.Mock()
    mock_async.get.return_value = {
        "processed_sources": 1,
        "rows": 10,
        "matched": 5,
        "created": 0,
        "dry_run": True,
    }
    mock_apply_async.return_value = mock_async

    response = self.client.post(
        "/api/v1/companies/reviews/run-opendata-ingestion/",
        {"dry_run": True},
        format="json",
    )

    self.assertEqual(response.status_code, status.HTTP_200_OK)
    mock_apply_async.assert_called_once()
    payload = mock_apply_async.call_args.kwargs.get("kwargs", {}).get("payload", {})
    self.assertTrue(payload.get("dry_run"))
    self.assertIsNone(payload.get("source_keys"))
    self.assertIsNone(payload.get("limit"))
    self.assertTrue(response.data["dry_run"])


class OpenDataSourceFilteringTests(TestCase):
    @mock.patch("companies.services.opendata_sources.requests.get")
    def test_ingest_opendata_sources_respects_company_id_filter(self, mock_get):
        CompanyUpdateCandidate.objects.all().delete()
        allowed_company = Company.objects.create(name="対象企業", corporate_number="1234500000000")
        skipped_company = Company.objects.create(name="除外企業", corporate_number="9999900000000")

        csv_content = (
            "法人番号,企業名,所在地,URL\n"
            "1234500000000,対象企業,東京都港区1-1-1,allowed.example\n"
            "9999900000000,除外企業,東京都新宿区2-2-2,skipped.example\n"
        )
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = csv_content.encode("utf-8")
        mock_response.raise_for_status = mock.Mock()
        mock_get.return_value = mock_response

        config = {
            "test_source": OpenDataSourceConfig.from_dict(
                "test_source",
                {
                    "label": "テスト自治体",
                    "url": "https://example.com/data.csv",
                    "format": "csv",
                    "encoding": "utf-8",
                    "source_detail": "local_gov_open_data_test",
                    "mappings": {
                        "corporate_number": "法人番号",
                        "name": "企業名",
                        "address": "所在地",
                        "website_url": "URL",
                    },
                },
            )
        }

        result = ingest_opendata_sources(
            source_keys=["test_source"],
            company_ids=[allowed_company.id],
            config_map=config,
        )

        self.assertEqual(result["matched"], 1)
        self.assertGreaterEqual(result["created"], 1)

        allowed_candidate = CompanyUpdateCandidate.objects.filter(
            company=allowed_company, field="website_url", source_detail="local_gov_open_data_test"
        ).first()
        self.assertIsNotNone(allowed_candidate)
        self.assertEqual(allowed_candidate.candidate_value, "https://allowed.example")

        skipped_exists = CompanyUpdateCandidate.objects.filter(company=skipped_company).exists()
        self.assertFalse(skipped_exists)


@override_settings(
    CORPORATE_NUMBER_API_TOKEN="dummy-token",
    CORPORATE_NUMBER_API_BASE_URL="https://example.com",
    CORPORATE_NUMBER_API_TIMEOUT=5,
    CORPORATE_NUMBER_API_MAX_RESULTS=3,
)
class CorporateNumberAPIClientTests(SimpleTestCase):
    def test_search_parses_results(self):
        payload = {
            "status": "200",
            "results": [
                {
                    "corporateNumber": "123456789012",
                    "name": "テスト株式会社",
                    "prefectureName": "東京都",
                    "sequenceNumber": "1",
                }
            ],
        }
        with mock.patch("companies.services.corporate_number_client.requests.get") as mock_get:
            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = payload
            mock_get.return_value = mock_response

            client = CorporateNumberAPIClient()
            results = client.search("テスト株式会社", prefecture="東京都")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["corporate_number"], "123456789012")
        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        params = kwargs["params"]
        self.assertEqual(params["name"], "テスト株式会社")
        self.assertEqual(params["address"], "東京都")
        self.assertEqual(params["limit"], "3")

    def test_search_handles_error_status(self):
        payload = {"status": "500", "message": "error"}
        with mock.patch("companies.services.corporate_number_client.requests.get") as mock_get:
            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = payload
            mock_get.return_value = mock_response

            client = CorporateNumberAPIClient()
            results = client.search("テスト株式会社")

        self.assertEqual(results, [])

    def test_search_requires_token(self):
        with override_settings(CORPORATE_NUMBER_API_TOKEN=""):
            client = CorporateNumberAPIClient(token="")
            with self.assertRaises(CorporateNumberAPIError):
                client.search("テスト株式会社")


class SelectBestMatchTests(SimpleTestCase):
    def test_selects_exact_match(self):
        candidates = [
            {"name": "株式会社A", "name_normalized": "株式会社a", "prefecture": "東京都", "corporate_number": "1"},
            {"name": "テスト株式会社", "name_normalized": "テスト株式会社", "prefecture": "東京都", "corporate_number": "2"},
        ]
        best = select_best_match(candidates, "テスト株式会社", prefecture="東京都")
        self.assertEqual(best["corporate_number"], "2")


@override_settings(CORPORATE_NUMBER_API_TOKEN="dummy-token")
class ImportCorporateNumbersCommandTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="テスト株式会社", prefecture="東京都")

    @mock.patch("companies.management.commands.import_corporate_numbers.ingest_corporate_number_candidates")
    @mock.patch("companies.management.commands.import_corporate_numbers.CorporateNumberAPIClient")
    def test_command_imports_candidates(self, mock_client_cls, mock_ingest):
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = [
            {
                "corporate_number": "123456789012",
                "name": "テスト株式会社",
                "name_normalized": "テスト株式会社",
                "prefecture": "東京都",
            }
        ]

        call_command("import_corporate_numbers")

        mock_ingest.assert_called_once()
        entries = mock_ingest.call_args[0][0]
        self.assertEqual(entries[0]["corporate_number"], "123456789012")
        self.assertEqual(entries[0]["company_id"], self.company.id)

    @mock.patch("companies.management.commands.import_corporate_numbers.ingest_corporate_number_candidates")
    @mock.patch("companies.management.commands.import_corporate_numbers.CorporateNumberAPIClient")
    def test_dry_run_skips_ingest(self, mock_client_cls, mock_ingest):
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = [
            {
                "corporate_number": "123456789012",
                "name": "テスト株式会社",
                "name_normalized": "テスト株式会社",
                "prefecture": "東京都",
            }
        ]

        call_command("import_corporate_numbers", "--dry-run")
        mock_ingest.assert_not_called()

    @override_settings(CORPORATE_NUMBER_API_TOKEN="")
    def test_missing_token_raises(self):
        with self.assertRaises(CommandError):
            call_command("import_corporate_numbers", "--company-id", str(self.company.id))


class RuleBasedIngestionTests(TestCase):
    def setUp(self) -> None:
        cache.clear()

    @override_settings(CORPORATE_NUMBER_API_TOKEN="dummy-token")
    @mock.patch("companies.management.commands.import_corporate_numbers.CorporateNumberAPIClient")
    def test_corporate_number_import_creates_rule_based_entries(self, client_cls):
        company = Company.objects.create(name="テスト株式会社", prefecture="", city="")

        mock_client = client_cls.return_value
        mock_client.search.return_value = [
            {
                "corporate_number": "1234567890123",
                "name": "テスト株式会社",
                "name_normalized": "テスト株式会社",
                "prefecture": "東京都",
                "raw": {
                    "prefectureName": "東京都",
                    "cityName": "渋谷区",
                    "streetNumber": "1-2-3",
                    "capitalStock": "10000000",
                    "phoneNumber": "03-1234-5678",
                },
            }
        ]

        result = run_corporate_number_import(
            company_ids=[company.id],
            force_refresh=True,
        )

        self.assertFalse(result["dry_run"])
        self.assertEqual(result["stats"]["matched"], 1)
        self.assertGreaterEqual(result["rule_entries_count"], 3)

        prefecture_candidate = CompanyUpdateCandidate.objects.filter(
            company=company, field="prefecture", source_detail="nta-api"
        ).first()
        self.assertIsNotNone(prefecture_candidate)
        self.assertEqual(prefecture_candidate.candidate_value, "東京都")

        city_candidate = CompanyUpdateCandidate.objects.filter(
            company=company, field="city", source_detail="nta-api"
        ).first()
        self.assertIsNotNone(city_candidate)
        self.assertIn("渋谷区", city_candidate.candidate_value)

        capital_candidate = CompanyUpdateCandidate.objects.filter(
            company=company, field="capital", source_detail="nta-api"
        ).first()
        self.assertIsNotNone(capital_candidate)
        self.assertEqual(capital_candidate.candidate_value, "10000000")

        phone_candidate = CompanyUpdateCandidate.objects.filter(
            company=company, field="phone", source_detail="nta-api"
        ).first()
        self.assertIsNotNone(phone_candidate)
        self.assertEqual(phone_candidate.candidate_value, "0312345678")

    @mock.patch("companies.services.opendata_sources.requests.get")
    def test_ingest_opendata_sources_creates_candidates(self, mock_get):
        company = Company.objects.create(name="サンプル株式会社", corporate_number="9876543210000")

        csv_content = (
            "法人番号,企業名,所在地,URL\n"
            "9876543210000,サンプル株式会社,東京都千代田区1-2-3,example.com\n"
        )
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = csv_content.encode("utf-8")
        mock_response.raise_for_status = mock.Mock()
        mock_get.return_value = mock_response

        config = {
            "test_source": OpenDataSourceConfig.from_dict(
                "test_source",
                {
                    "label": "テスト自治体",
                    "url": "https://example.com/data.csv",
                    "format": "csv",
                    "encoding": "utf-8",
                    "source_detail": "local_gov_open_data_test",
                    "mappings": {
                        "corporate_number": "法人番号",
                        "name": "企業名",
                        "address": "所在地",
                        "website_url": "URL",
                    },
                },
            )
        }

        result = ingest_opendata_sources(source_keys=["test_source"], config_map=config)

        self.assertFalse(result["dry_run"])
        self.assertEqual(result["matched"], 1)
        self.assertGreaterEqual(result["created"], 2)

        website_candidate = CompanyUpdateCandidate.objects.filter(
            company=company, field="website_url", source_detail="local_gov_open_data_test"
        ).first()
        self.assertIsNotNone(website_candidate)
        self.assertEqual(website_candidate.candidate_value, "https://example.com")

        prefecture_candidate = CompanyUpdateCandidate.objects.filter(
            company=company, field="prefecture", source_detail="local_gov_open_data_test"
        ).first()
        self.assertIsNotNone(prefecture_candidate)
        self.assertEqual(prefecture_candidate.candidate_value, "東京都")
