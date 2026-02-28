from django.db import models


class IdempotencyRecord(models.Model):
    tool_name = models.CharField(max_length=120)
    idempotency_key = models.CharField(max_length=120)
    args_hash = models.CharField(max_length=64)
    response_payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "storage_idempotency_record"
        constraints = [
            models.UniqueConstraint(
                fields=["tool_name", "idempotency_key"],
                name="uniq_storage_idempotency_tool_key",
            )
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.tool_name}:{self.idempotency_key}"
