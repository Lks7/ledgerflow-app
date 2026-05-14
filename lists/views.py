from datetime import datetime

from django.contrib import messages
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .services import (
    add_item,
    ai_analyze_items,
    create_subscription,
    delete_item,
    delete_subscription,
    get_item,
    list_items,
    list_subscriptions,
    pending_summary,
    renew_subscription,
    subscription_summary,
    update_item,
    update_status,
    update_subscription,
)


def shopping_list(request):
    status = request.GET.get("status", "")
    context = {
        "status": status,
        "items": list_items(status),
        "summary": pending_summary(),
        "today": datetime.now().strftime("%Y-%m-%d"),
    }
    return render(request, "lists/shopping_list.html", context)


def subscription_list(request):
    status = request.GET.get("status", "")
    context = {
        "status": status,
        "items": list_subscriptions(status),
        "summary": subscription_summary(),
        "today": datetime.now().strftime("%Y-%m-%d"),
    }
    return render(request, "lists/subscription_list.html", context)


def subscription_create(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")
    create_subscription(
        name=request.POST.get("name", ""),
        service_type=request.POST.get("service_type", ""),
        billing_cycle=request.POST.get("billing_cycle", "monthly"),
        custom_days=request.POST.get("custom_days", "30"),
        price=request.POST.get("price", "0"),
        start_date=request.POST.get("start_date", datetime.now().strftime("%Y-%m-%d")),
        next_renewal_date=request.POST.get(
            "next_renewal_date", datetime.now().strftime("%Y-%m-%d")
        ),
        expiry_date=request.POST.get("expiry_date", ""),
        note=request.POST.get("note", ""),
    )
    messages.success(request, "订阅服务已添加")
    return redirect("subscription_list")


@require_POST
def subscription_update(request):
    ok = update_subscription(
        item_id=request.POST.get("item_id", ""),
        name=request.POST.get("name", ""),
        service_type=request.POST.get("service_type", ""),
        billing_cycle=request.POST.get("billing_cycle", "monthly"),
        custom_days=request.POST.get("custom_days", "30"),
        price=request.POST.get("price", "0"),
        start_date=request.POST.get("start_date", datetime.now().strftime("%Y-%m-%d")),
        next_renewal_date=request.POST.get(
            "next_renewal_date", datetime.now().strftime("%Y-%m-%d")
        ),
        expiry_date=request.POST.get("expiry_date", ""),
        status=request.POST.get("status", "active"),
        note=request.POST.get("note", ""),
    )
    if not ok:
        messages.error(request, "更新失败：未找到订阅服务")
        return HttpResponseBadRequest("未找到订阅服务")
    messages.success(request, "订阅服务已更新")
    return redirect("subscription_list")


@require_POST
def subscription_delete(request):
    delete_subscription(request.POST.get("item_id", ""))
    messages.success(request, "订阅服务已删除")
    return redirect("subscription_list")


@require_POST
def subscription_renew(request):
    ok = renew_subscription(request.POST.get("item_id", ""))
    if not ok:
        messages.error(request, "续订失败：未找到订阅服务")
        return HttpResponseBadRequest("未找到订阅服务")
    messages.success(request, "订阅日期已自动顺延")
    return redirect("subscription_list")


def shopping_create(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")
    add_item(
        name=request.POST.get("name", ""),
        qty=request.POST.get("qty", "1"),
        est_price=request.POST.get("est_price", "0"),
        actual_price=request.POST.get("actual_price", "0"),
        priority=request.POST.get("priority", "normal"),
        planned_date=request.POST.get(
            "planned_date", datetime.now().strftime("%Y-%m-%d")
        ),
        platform=request.POST.get("platform", ""),
        note=request.POST.get("note", ""),
    )
    messages.success(request, "清单项已添加")
    return redirect("shopping_list")


@require_POST
def shopping_update(request):
    ok = update_item(
        item_id=request.POST.get("item_id", ""),
        name=request.POST.get("name", ""),
        qty=request.POST.get("qty", "1"),
        est_price=request.POST.get("est_price", "0"),
        actual_price=request.POST.get("actual_price", "0"),
        priority=request.POST.get("priority", "normal"),
        planned_date=request.POST.get("planned_date", ""),
        platform=request.POST.get("platform", ""),
        note=request.POST.get("note", ""),
    )
    if not ok:
        messages.error(request, "更新失败：未找到清单项")
        return HttpResponseBadRequest("未找到清单项")
    messages.success(request, "清单项已更新")
    return redirect("shopping_list")


def shopping_update_status(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")
    update_status(
        request.POST.get("item_id", ""), request.POST.get("status", "pending")
    )
    messages.success(request, "状态已更新")
    return redirect("shopping_list")


@require_POST
def shopping_delete(request):
    item_id = request.POST.get("item_id", "")
    delete_item(item_id)
    messages.success(request, "清单项已删除")
    return redirect("shopping_list")


def ai_analyze(request):
    """JSON endpoint: AI analysis of current pending shopping list."""
    items = list_items(status="pending")
    result = ai_analyze_items(items)
    return JsonResponse(result)


def to_journal_draft(request):
    item_id = request.GET.get("item_id", "")
    item = get_item(item_id)
    if not item:
        return HttpResponseBadRequest("未找到清单项")

    total = item.get("qty", 1) * item.get("est_price", 0)
    from urllib.parse import urlencode

    params = urlencode(
        {
            "desc": f"购买: {item.get('name', '')}",
            "amount": f"{total:.2f}",
            "tags": "shopping",
            "source": "shopping_list",
        }
    )
    return redirect(f"/journals/new?{params}")
