from .models import AIConfig


DEFAULT_PROMPT = (
    "你是专业个人财务顾问。请根据用户的收支、分类、趋势数据，"
    "输出可执行、可量化的消费建议，包含洞察、原因、三条行动、目标。"
)


def get_or_create_config() -> AIConfig:
    config = AIConfig.objects.order_by("id").first()
    if config:
        return config
    return AIConfig.objects.create(
        provider="google",
        api_base_url="",
        api_key="",
        model_name="gemini-1.5-flash",
        system_prompt=DEFAULT_PROMPT,
    )


def save_config_from_post(post_data) -> AIConfig:
    config = get_or_create_config()
    config.provider = (post_data.get("provider") or "google").strip() or "google"
    config.api_base_url = (post_data.get("api_base_url") or "").strip()
    config.api_key = (post_data.get("api_key") or "").strip()
    config.model_name = (post_data.get("model_name") or "gemini-1.5-flash").strip()
    config.system_prompt = (post_data.get("system_prompt") or DEFAULT_PROMPT).strip()
    config.save()
    return config


def masked_key(api_key: str) -> str:
    if not api_key:
        return "未设置"
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"
