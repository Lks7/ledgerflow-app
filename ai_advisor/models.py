from django.db import models


class AIConfig(models.Model):
    provider = models.CharField(max_length=50, default="google")
    api_base_url = models.CharField(max_length=500, blank=True, default="")
    api_key = models.CharField(max_length=500, blank=True, default="")
    model_name = models.CharField(max_length=120, default="gemini-1.5-flash")
    system_prompt = models.TextField(
        default=(
            "你是专业个人财务顾问。请根据用户的收支、分类、趋势数据，"
            "输出可执行、可量化的消费建议。"
        )
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_advisor_config"

    def __str__(self):
        return f"AIConfig({self.provider}, {self.model_name})"


class AIAdviceSnapshot(models.Model):
    month = models.CharField(max_length=7, unique=True)
    payload = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_advisor_snapshot"
        ordering = ["-month"]

    def __str__(self):
        return f"AIAdviceSnapshot({self.month})"
