from datetime import datetime

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .config_service import get_or_create_config, masked_key, save_config_from_post
from .services import generate_monthly_advice, test_ai_connection


def monthly_advice(request):
    month = request.GET.get("month") or datetime.now().strftime("%Y-%m")
    force = request.GET.get("refresh") == "1"
    return JsonResponse(generate_monthly_advice(month, force_refresh=force))


def monthly_advice_ui(request):
    month = request.GET.get("month") or datetime.now().strftime("%Y-%m")
    force = request.GET.get("refresh") == "1"
    advice = generate_monthly_advice(month, force_refresh=force)
    return render(
        request,
        "ai_advisor/partials/advice_card.html",
        {"advice": advice},
    )


def config_page(request):
    test_result = None
    if request.method == "POST":
        action = request.POST.get("action", "save")
        save_config_from_post(request.POST)
        if action == "test":
            test_result = test_ai_connection()
            if test_result.get("ok"):
                messages.success(request, "AI 连接测试成功")
            else:
                messages.error(
                    request, f"AI 连接测试失败：{test_result.get('message', '')}"
                )
        else:
            messages.success(request, "AI 配置已保存")
            return redirect("ai_config")

    config = get_or_create_config()
    return render(
        request,
        "ai_advisor/config.html",
        {
            "config": config,
            "api_key_masked": masked_key(config.api_key),
            "test_result": test_result,
        },
    )
