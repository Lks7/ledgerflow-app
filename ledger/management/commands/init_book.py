from django.core.management.base import BaseCommand
from django.db import transaction

from ai_advisor.models import AIAdviceSnapshot
from ledger.models import Journal, JournalEntry, JournalLog, JournalTransfer
from ledger.services import recalculate_account_balances
from lists.models import ShoppingItem
from storage.models import IdempotencyRecord


class Command(BaseCommand):
    help = (
        "Initialize book data by clearing transactional data while keeping "
        "accounts/categories/tags."
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
                    "AI snapshots and idempotency records. "
                    "Accounts/categories/tags will be kept."
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
            recalculate_account_balances()

        self.stdout.write(self.style.SUCCESS("Book initialized successfully."))
        self.stdout.write(
            "Kept: accounts, categories, tags. Cleared: journals/logs/shopping/AI snapshots/idempotency."
        )
