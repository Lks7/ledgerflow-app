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
