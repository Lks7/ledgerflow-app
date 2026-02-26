"""
Import existing JSON data from the data/ directory into SQLite via Django ORM.
Run with:
    .venv\\Scripts\\python manage.py shell < scripts/import_json_to_sqlite.py
  or:
    .venv\\Scripts\\python scripts/import_json_to_sqlite.py
"""
import os
import sys
import uuid
import json
from pathlib import Path

# Bootstrap Django if run as standalone script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
    import django
    django.setup()

from decimal import Decimal
from ledger.models import Account, Category, Journal, JournalEntry, JournalTransfer
from lists.models import ShoppingItem

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def load_json(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def import_accounts():
    data = load_json(DATA_DIR / "accounts.json")
    created = 0
    for item in data:
        account_id = item.get("id") or str(uuid.uuid4())
        # Clean out computed fields that don't belong on the model
        _, was_created = Account.objects.update_or_create(
            id=account_id,
            defaults=dict(
                name=item.get("name", ""),
                type=item.get("type", "asset"),
                currency=item.get("currency", "CNY"),
                status=item.get("status", "active"),
                opening_balance=Decimal(str(item.get("opening_balance", "0"))),
                balance=Decimal(str(item.get("balance", "0"))),
                note=item.get("note", ""),
            ),
        )
        if was_created:
            created += 1
    print(f"Accounts: {len(data)} processed, {created} created")


def import_categories():
    data = load_json(DATA_DIR / "categories.json")
    created = 0
    for item in data:
        _, was_created = Category.objects.update_or_create(
            id=item.get("id", str(uuid.uuid4())),
            defaults=dict(
                name=item.get("name", ""),
                group=item.get("group", ""),
                budget_monthly=Decimal(str(item.get("budget_monthly", "0"))),
            ),
        )
        if was_created:
            created += 1
    print(f"Categories: {len(data)} processed, {created} created")


def import_journals():
    journals_dir = DATA_DIR / "journals"
    if not journals_dir.exists():
        print("No journals directory found, skipping")
        return

    total_journals = 0
    total_entries = 0
    total_transfers = 0

    for json_file in sorted(journals_dir.glob("*.json")):
        journals = load_json(json_file)
        for j in journals:
            journal_id = j.get("id", str(uuid.uuid4()))
            tags = j.get("tags") or []

            journal, _ = Journal.objects.update_or_create(
                id=journal_id,
                defaults=dict(
                    date=j.get("date"),
                    description=j.get("description", ""),
                    source=j.get("source", "manual"),
                    tags_raw=",".join(t for t in tags if t),
                ),
            )
            # Delete & recreate entries and transfers to avoid duplication
            journal.entries.all().delete()
            journal.transfers.all().delete()

            for e in j.get("entries", []):
                account_id = e.get("account_id", "")
                try:
                    account = Account.objects.get(id=account_id)
                except Account.DoesNotExist:
                    print(f"  Warning: Account '{account_id}' not found, skipping entry")
                    continue
                category = None
                cat_id = e.get("category_id", "")
                if cat_id:
                    category = Category.objects.filter(id=cat_id).first()
                JournalEntry.objects.create(
                    journal=journal,
                    account=account,
                    category=category,
                    debit=Decimal(str(e.get("debit", "0"))),
                    credit=Decimal(str(e.get("credit", "0"))),
                    currency=e.get("currency", "CNY"),
                    note=e.get("note", ""),
                )
                total_entries += 1

            for t in j.get("transfers", []):
                try:
                    from_acc = Account.objects.get(id=t.get("from_account_id", ""))
                    to_acc = Account.objects.get(id=t.get("to_account_id", ""))
                except Account.DoesNotExist as exc:
                    print(f"  Warning: Transfer account not found: {exc}, skipping")
                    continue
                JournalTransfer.objects.create(
                    journal=journal,
                    from_account=from_acc,
                    to_account=to_acc,
                    amount=Decimal(str(t.get("amount", "0"))),
                    currency=t.get("currency", "CNY"),
                    note=t.get("note", ""),
                )
                total_transfers += 1

            total_journals += 1

    print(f"Journals: {total_journals}, Entries: {total_entries}, Transfers: {total_transfers}")


def import_shopping():
    data = load_json(DATA_DIR / "lists" / "shopping.json")
    created = 0
    for item in data:
        item_id = item.get("id", str(uuid.uuid4()))
        _, was_created = ShoppingItem.objects.update_or_create(
            id=item_id,
            defaults=dict(
                name=item.get("name", ""),
                qty=int(item.get("qty", 1)),
                est_price=Decimal(str(item.get("est_price", "0"))),
                priority=item.get("priority", "normal"),
                status=item.get("status", "pending"),
                planned_date=item.get("planned_date", "") or "",
                note=item.get("note", ""),
            ),
        )
        if was_created:
            created += 1
    print(f"ShoppingItems: {len(data)} processed, {created} created")


if __name__ == "__main__":
    print("=== Importing JSON data into SQLite ===")
    import_accounts()
    import_categories()
    import_journals()
    import_shopping()
    print("=== Done ===")
