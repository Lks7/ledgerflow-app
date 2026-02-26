from django.db import models


class Account(models.Model):
    ACCOUNT_TYPES = [
        ("asset", "资产"),
        ("liability", "负债"),
        ("income", "收入"),
        ("expense", "支出"),
    ]
    STATUSES = [
        ("active", "启用"),
        ("inactive", "停用"),
    ]

    # Use a CharField PK so we can keep slug IDs like "cash", "alipay" etc.
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default="asset")
    currency = models.CharField(max_length=10, default="CNY")
    status = models.CharField(max_length=20, choices=STATUSES, default="active")
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    note = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ledger_account"
        ordering = ["type", "name"]

    def __str__(self):
        return f"{self.name} ({self.type})"


class Category(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=200)
    icon = models.CharField(max_length=20, blank=True, default="")
    group = models.CharField(max_length=100, blank=True, default="")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    budget_monthly = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "ledger_category"
        ordering = ["group", "name"]

    def __str__(self):
        return self.name


class Journal(models.Model):
    id = models.CharField(max_length=100, primary_key=True)  # UUID string
    date = models.DateField()
    description = models.CharField(max_length=500, blank=True, default="")
    source = models.CharField(max_length=100, blank=True, default="manual")
    # Store tags as a comma-separated string for simplicity
    tags_raw = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ledger_journal"
        ordering = ["-date", "-created_at"]

    def get_tags(self):
        return [t for t in self.tags_raw.split(",") if t.strip()]

    def set_tags(self, tags: list):
        self.tags_raw = ",".join(t.strip() for t in tags if t.strip())

    def __str__(self):
        return f"{self.date} – {self.description}"


class JournalEntry(models.Model):
    journal = models.ForeignKey(
        Journal, on_delete=models.CASCADE, related_name="entries"
    )
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="entries"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entries",
    )
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="CNY")
    note = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "ledger_journal_entry"

    def __str__(self):
        return f"Entry({self.account_id}) D:{self.debit} C:{self.credit}"


class JournalTransfer(models.Model):
    journal = models.ForeignKey(
        Journal, on_delete=models.CASCADE, related_name="transfers"
    )
    from_account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="transfers_out"
    )
    to_account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="transfers_in"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10, default="CNY")
    note = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "ledger_journal_transfer"

    def __str__(self):
        return f"Transfer {self.from_account_id}→{self.to_account_id} {self.amount}"


class JournalLog(models.Model):
    timestamp = models.DateTimeField()
    action = models.CharField(max_length=50)
    journal_id = models.CharField(max_length=100)
    date = models.CharField(max_length=20, blank=True, default="")
    description = models.CharField(max_length=500, blank=True, default="")
    entries = models.JSONField(default=list)

    class Meta:
        db_table = "ledger_journal_log"
        ordering = ["-timestamp", "-id"]

    def __str__(self):
        return f"{self.timestamp} {self.action} {self.journal_id}"
