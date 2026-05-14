from django.db import models


class TodoItem(models.Model):
    QUADRANT_CHOICES = [
        ("q1", "紧急且重要"),
        ("q2", "重要不紧急"),
        ("q3", "紧急不重要"),
        ("q4", "不紧急不重要"),
    ]
    STATUS_CHOICES = [
        ("pending", "进行中"),
        ("done", "已完成"),
    ]
    CATEGORY_CHOICES = [
        ("work", "工作"),
        ("study", "学习"),
        ("life", "生活"),
        ("finance", "财务"),
        ("health", "健康"),
        ("goal", "目标"),
        ("other", "其他"),
    ]

    id = models.CharField(max_length=100, primary_key=True)  # UUID string
    title = models.CharField(max_length=300)
    quadrant = models.CharField(
        max_length=20, choices=QUADRANT_CHOICES, default="q1"
    )
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, default="other"
    )
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    note = models.CharField(max_length=500, blank=True, default="")
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "todos_item"
        ordering = ["status", "quadrant", "sort_order", "-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_quadrant_display()}) [{self.status}]"
