import shutil
from pathlib import Path

from django.test import TestCase, override_settings

from .models import Category
from .services import (
    create_account,
    create_journal,
    delete_account,
    list_journal_logs,
    list_journals,
    set_account_status,
    update_journal_metadata,
)


@override_settings(DATA_DIR="D:/project/memory/test_data")
class LedgerServiceTests(TestCase):
    def setUp(self):
        shutil.rmtree(Path("D:/project/memory/test_data"), ignore_errors=True)
        Category.objects.create(id="food", name="餐饮", group="支出")

    def test_reject_unbalanced_journal(self):
        journal, error = create_journal(
            date="2026-02-01",
            description="不平衡测试",
            source="manual",
            tags="",
            entries=[
                {
                    "account_id": "cash",
                    "category_id": "food",
                    "debit": "100",
                    "credit": "0",
                },
                {
                    "account_id": "wechat",
                    "category_id": "food",
                    "debit": "0",
                    "credit": "90",
                },
            ],
        )
        self.assertIsNone(journal)
        self.assertIn("借贷不平衡", error)

    def test_create_balanced_journal(self):
        journal, error = create_journal(
            date="2026-02-01",
            description="平衡测试",
            source="manual",
            tags="food",
            entries=[
                {
                    "account_id": "expense",
                    "category_id": "food",
                    "debit": "88",
                    "credit": "0",
                },
                {
                    "account_id": "cash",
                    "category_id": "food",
                    "debit": "0",
                    "credit": "88",
                },
            ],
        )
        self.assertEqual(error, "")
        self.assertIsNotNone(journal)
        self.assertEqual(len(list_journals("2026-02")), 1)

    def test_delete_used_account_blocked(self):
        create_journal(
            date="2026-02-01",
            description="平衡测试",
            source="manual",
            tags="food",
            entries=[
                {
                    "account_id": "expense",
                    "category_id": "food",
                    "debit": "20",
                    "credit": "0",
                },
                {
                    "account_id": "cash",
                    "category_id": "food",
                    "debit": "0",
                    "credit": "20",
                },
            ],
        )
        ok, error = delete_account("cash")
        self.assertFalse(ok)
        self.assertIn("已有记账记录", error)

    def test_inactive_account_cannot_post_journal(self):
        account, _ = create_account("测试账户", "asset", "CNY", "100")
        self.assertIsNotNone(account)
        ok, _ = set_account_status(account["id"], "inactive")
        self.assertTrue(ok)
        journal, error = create_journal(
            date="2026-02-02",
            description="停用账户测试",
            source="manual",
            tags="",
            entries=[
                {
                    "account_id": "expense",
                    "category_id": "food",
                    "debit": "10",
                    "credit": "0",
                },
                {
                    "account_id": account["id"],
                    "category_id": "food",
                    "debit": "0",
                    "credit": "10",
                },
            ],
        )
        self.assertIsNone(journal)
        self.assertIn("账户已停用", error)

    def test_journal_create_writes_log(self):
        create_journal(
            date="2026-02-01",
            description="日志测试",
            source="manual",
            tags="",
            entries=[
                {
                    "account_id": "expense",
                    "category_id": "food",
                    "debit": "12",
                    "credit": "0",
                },
                {
                    "account_id": "cash",
                    "category_id": "food",
                    "debit": "0",
                    "credit": "12",
                },
            ],
        )
        logs = list_journal_logs()
        self.assertGreaterEqual(len(logs), 1)
        self.assertEqual(logs[0].get("action"), "create")

    def test_transfer_auto_generates_balanced_entries(self):
        journal, error = create_journal(
            date="2026-02-09",
            description="账户转账",
            source="manual",
            tags="转账,测试",
            entries=[],
            transfer_lines=[
                {
                    "from_account_id": "wechat",
                    "to_account_id": "cash",
                    "amount": "120.50",
                    "currency": "CNY",
                    "note": "提现",
                }
            ],
        )
        self.assertEqual(error, "")
        self.assertIsNotNone(journal)
        self.assertEqual(len(journal.get("entries", [])), 2)
        self.assertEqual(journal["entries"][0]["account_id"], "cash")
        self.assertEqual(journal["entries"][0]["debit"], "120.50")
        self.assertEqual(journal["entries"][1]["account_id"], "wechat")
        self.assertEqual(journal["entries"][1]["credit"], "120.50")

    def test_update_journal_metadata_changes_tags_and_category(self):
        journal, error = create_journal(
            date="2026-02-10",
            description="元数据测试",
            source="manual",
            tags="旧标签",
            entries=[
                {
                    "account_id": "expense",
                    "category_id": "food",
                    "debit": "30",
                    "credit": "0",
                },
                {
                    "account_id": "cash",
                    "category_id": "food",
                    "debit": "0",
                    "credit": "30",
                },
            ],
        )
        self.assertEqual(error, "")
        self.assertIsNotNone(journal)

        updated, update_error = update_journal_metadata(
            journal["id"], "新标签,周末", ""
        )
        self.assertEqual(update_error, "")
        self.assertEqual(updated["tags"], ["新标签", "周末"])
        self.assertTrue(
            all(e.get("category_id") in (None, "") for e in updated["entries"])
        )
