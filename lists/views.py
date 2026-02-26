from datetime import datetime

from django.contrib import messages
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .services import (
    add_item,
    ai_analyze_items,
    delete_item,
    get_item,
    list_items,
    pending_summary,
    update_item,
    update_status,
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
