from django.db import models


class ShoppingItem(models.Model):
    PRIORITY_CHOICES = [("high", "高"), ("normal", "普通"), ("low", "低")]
    STATUS_CHOICES = [("pending", "待购"), ("done", "已购"), ("skipped", "跳过")]

    id = models.CharField(max_length=100, primary_key=True)  # UUID string
    name = models.CharField(max_length=300)
    qty = models.IntegerField(default=1)
    est_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="normal"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    planned_date = models.CharField(max_length=20, blank=True, default="")
    platform = models.CharField(max_length=120, blank=True, default="")
    note = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lists_shopping_item"
        ordering = ["status", "priority", "-created_at"]

    def __str__(self):
        return f"{self.name} x{self.qty} ({self.status})"


class SubscriptionService(models.Model):
    CYCLE_CHOICES = [
        ("monthly", "月度"),
        ("quarterly", "季度"),
        ("yearly", "年度"),
        ("custom", "自定义"),
    ]
    STATUS_CHOICES = [
        ("active", "进行中"),
        ("paused", "暂停"),
        ("cancelled", "已取消"),
    ]

    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=200)
    service_type = models.CharField(max_length=120, blank=True, default="")
    billing_cycle = models.CharField(
        max_length=20, choices=CYCLE_CHOICES, default="monthly"
    )
    custom_days = models.IntegerField(default=30)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    next_renewal_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    note = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lists_subscription_service"
        ordering = ["next_renewal_date", "name"]

    def __str__(self):
        return f"{self.name} ({self.billing_cycle})"
