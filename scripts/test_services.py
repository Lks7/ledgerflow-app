import os
import sys
from pathlib import Path

# Bootstrap Django
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
import django
django.setup()

from ledger.services import get_accounts, list_journals
from lists.services import list_items
from analytics.services import monthly_summary

print("ACCOUNTS:")
accounts = get_accounts()
print(f"Count: {len(accounts)}")
if accounts:
    print(accounts[0])

print("\nJOURNALS:")
journals = list_journals("2026-02")
print(f"Count: {len(journals)}")

print("\nLIST ITEMS:")
items = list_items()
print(f"Count: {len(items)}")

print("\nANALYTICS:")
summary = monthly_summary("2026-02")
print(f"Summary keys: {list(summary.keys())}")
print(f"Net: {summary['net']}")

print("\nAll passed basic import and execution.")
