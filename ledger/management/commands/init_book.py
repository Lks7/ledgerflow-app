from django.core.management.base import BaseCommand
from django.db import transaction

from ai_advisor.models import AIAdviceSnapshot
from ledger.models import (
    Account,
    Category,
    Journal,
    JournalEntry,
    JournalLog,
    JournalTransfer,
    Tag,
)
from lists.models import ShoppingItem
from storage.models import IdempotencyRecord


class Command(BaseCommand):
    help = (
        "Initialize book data by clearing transactional data while keeping "
        "a minimal usable account structure."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Confirm execution without interactive prompt.",
        )

    def handle(self, *args, **options):
        if not options.get("yes"):
            self.stdout.write(
                self.style.WARNING(
                    "This will clear journals, journal logs, shopping items, "
                    "AI snapshots, idempotency records, categories and tags. "
                    "Account balances will be reset to 0."
                )
            )
            confirmed = input("Type 'YES' to continue: ").strip()
            if confirmed != "YES":
                self.stdout.write(self.style.ERROR("Cancelled."))
                return

        with transaction.atomic():
            JournalEntry.objects.all().delete()
            JournalTransfer.objects.all().delete()
            Journal.objects.all().delete()
            JournalLog.objects.all().delete()
            ShoppingItem.objects.all().delete()
            AIAdviceSnapshot.objects.all().delete()
            IdempotencyRecord.objects.all().delete()
            Category.objects.all().delete()
            Tag.objects.all().delete()
            Account.objects.all().update(opening_balance=0, balance=0)

        self.stdout.write(self.style.SUCCESS("Book initialized successfully."))
        self.stdout.write(
            "Cleared: journals/logs/shopping/AI snapshots/idempotency/categories/tags; reset account balances to 0."
        )
