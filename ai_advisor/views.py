from datetime import date, datetime

from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import redirect, render

from ledger.services import get_accounts, list_journals

from .config_service import get_or_create_config, masked_key, save_config_from_post
from .services import (
    build_reconcile_preview,
    commit_reconcile,
    generate_monthly_advice,
    test_ai_connection,
)


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


def _reconcile_form_context():
    today = date.today()
    return {
        "accounts": get_accounts(),
        "default_start_date": (today.fromordinal(today.toordinal() - 30)).isoformat(),
        "default_end_date": today.isoformat(),
    }


def reconcile_form(request):
    return render(
        request, "ai_advisor/partials/reconcile_form.html", _reconcile_form_context()
    )


def reconcile_preview(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")

    account_id = (request.POST.get("account_id") or "").strip()
    start_date = (request.POST.get("start_date") or "").strip()
    end_date = (request.POST.get("end_date") or "").strip()
    if not account_id or not end_date:
        return HttpResponseBadRequest("参数不完整")

    target = None
    for acc in get_accounts():
        if acc.get("id") == account_id:
            target = acc
            break
    if not target:
        return HttpResponseBadRequest("账户不存在")

    month = end_date[:7]
    rows = list_journals(month)
    scoped = []
    for j in rows:
        j_date = j.get("date") or ""
        if start_date and j_date < start_date:
            continue
        if j_date > end_date:
            continue
        if any(e.get("account_id") == account_id for e in j.get("entries", [])):
            scoped.append(j)

    preview = build_reconcile_preview(target, scoped)
    request.session["ai_reconcile_preview"] = {
        "preview": preview,
        "end_date": end_date,
    }
    return render(
        request,
        "ai_advisor/partials/reconcile_card.html",
        {
            "preview": preview,
            "account": target,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


def reconcile_commit(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")

    if request.POST.get("confirm") != "true":
        return HttpResponseBadRequest("需要确认参数")

    data = request.session.get("ai_reconcile_preview") or {}
    preview = data.get("preview")
    end_date = data.get("end_date")
    if not preview or not end_date:
        return HttpResponseBadRequest("没有可提交的平账预览")

    result = commit_reconcile(preview, end_date)
    if not result.get("ok"):
        return render(
            request,
            "ai_advisor/partials/reconcile_commit_result.html",
            {"ok": False, "message": result.get("error") or "平账失败"},
            status=400,
        )

    request.session.pop("ai_reconcile_preview", None)
    return render(
        request,
        "ai_advisor/partials/reconcile_commit_result.html",
        {
            "ok": True,
            "message": result.get("message", "平账已入库"),
            "journal": result.get("journal"),
        },
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
