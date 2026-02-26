import shutil
from pathlib import Path

from django.test import TestCase, override_settings

from ledger.models import Category
from ledger.services import create_journal

from .services import monthly_summary


@override_settings(DATA_DIR="D:/project/memory/test_data")
class AnalyticsServiceTests(TestCase):
    def setUp(self):
        shutil.rmtree(Path("D:/project/memory/test_data"), ignore_errors=True)
        Category.objects.create(id="salary", name="工资", group="收入")
        Category.objects.create(id="food", name="餐饮", group="支出")

    def test_monthly_summary_totals(self):
        create_journal(
            date="2026-03-02",
            description="工资",
            source="manual",
            tags="income",
            entries=[
                {
                    "account_id": "cash",
                    "category_id": "salary",
                    "debit": "5000",
                    "credit": "0",
                },
                {
                    "account_id": "income",
                    "category_id": "salary",
                    "debit": "0",
                    "credit": "5000",
                },
            ],
        )
        create_journal(
            date="2026-03-03",
            description="午餐",
            source="manual",
            tags="food",
            entries=[
                {
                    "account_id": "expense",
                    "category_id": "food",
                    "debit": "50",
                    "credit": "0",
                },
                {
                    "account_id": "cash",
                    "category_id": "food",
                    "debit": "0",
                    "credit": "50",
                },
            ],
        )
        summary = monthly_summary("2026-03")
        self.assertEqual(summary["income"], 5000.0)
        self.assertEqual(summary["expense"], 50.0)
        self.assertEqual(summary["net"], 4950.0)
        self.assertEqual(summary["journal_count"], 2)
