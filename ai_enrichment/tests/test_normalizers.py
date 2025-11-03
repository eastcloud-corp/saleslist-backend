from django.test import SimpleTestCase

from ai_enrichment.normalizers import normalize_candidate_value


class NormalizerTests(SimpleTestCase):
    def test_established_year_with_suffix(self):
        self.assertEqual(normalize_candidate_value("established_year", "2024年"), "2024")

    def test_established_year_with_full_date(self):
        self.assertEqual(normalize_candidate_value("established_year", "2024/03/22"), "2024")

    def test_established_year_wareki(self):
        self.assertEqual(
            normalize_candidate_value("established_year", "平成36年(2024年)"), "2024"
        )

    def test_established_year_digits_only(self):
        self.assertEqual(normalize_candidate_value("established_year", "2024322"), "2024")

    def test_capital_plain_number(self):
        self.assertEqual(normalize_candidate_value("capital", "6500000"), "6500000")

    def test_capital_with_currency(self):
        self.assertEqual(normalize_candidate_value("capital", "6,500,000円"), "6500000")

    def test_capital_million_unit(self):
        self.assertEqual(normalize_candidate_value("capital", "650万円"), "6500000")

    def test_capital_oku_unit(self):
        self.assertEqual(normalize_candidate_value("capital", "0.65億円"), "65000000")

    def test_capital_unknown(self):
        self.assertIsNone(normalize_candidate_value("capital", "未公開"))

    def test_contact_person_name_removes_role_prefix(self):
        self.assertEqual(
            normalize_candidate_value("contact_person_name", "代表取締役 菊地航輔"), "菊地航輔"
        )

    def test_contact_person_name_removes_parentheses(self):
        self.assertEqual(
            normalize_candidate_value("contact_person_name", "菊地航輔（代表取締役）"), "菊地航輔"
        )

    def test_contact_person_position_splits_by_separator(self):
        self.assertEqual(
            normalize_candidate_value("contact_person_position", "代表取締役／CEO"), "代表取締役"
        )

    def test_contact_person_position_removes_name(self):
        self.assertEqual(
            normalize_candidate_value("contact_person_position", "代表取締役 菊地航輔"),
            "代表取締役",
        )
