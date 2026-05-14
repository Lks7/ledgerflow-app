from datetime import date

from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import TodoItem
from .services import (
    create_todo,
    delete_todo,
    list_todos,
    move_quadrant,
    todo_summary,
    toggle_todo,
    update_todo,
)


def todo_list(request):
    """Main todo page with quadrant and list views."""
    status_filter = request.GET.get("status", "")
    category_filter = request.GET.get("category", "")

    summary = todo_summary()

    # For quadrant view: group pending todos by quadrant
    pending_todos = TodoItem.objects.filter(status="pending").order_by(
        "sort_order", "-created_at"
    )
    q1_items = list(pending_todos.filter(quadrant="q1"))
    q2_items = list(pending_todos.filter(quadrant="q2"))
    q3_items = list(pending_todos.filter(quadrant="q3"))
    q4_items = list(pending_todos.filter(quadrant="q4"))

    # Mark overdue items
    today = date.today()
    for items_list in [q1_items, q2_items, q3_items, q4_items]:
        for item in items_list:
            item.is_overdue = item.due_date and item.due_date < today
            item.is_due_today = item.due_date and item.due_date == today

    # For list view: all todos
    if status_filter:
        all_items = TodoItem.objects.filter(status=status_filter)
    else:
        all_items = TodoItem.objects.all()
    if category_filter:
        all_items = all_items.filter(category=category_filter)

    all_items = list(all_items.order_by("status", "quadrant", "sort_order", "-created_at"))
    for item in all_items:
        item.is_overdue = (
            item.due_date and item.due_date < today and item.status == "pending"
        )
        item.is_due_today = item.due_date and item.due_date == today

    # Done items (for the bottom section)
    done_items = list(
        TodoItem.objects.filter(status="done").order_by("-completed_at")[:20]
    )

    context = {
        "summary": summary,
        "q1_items": q1_items,
        "q2_items": q2_items,
        "q3_items": q3_items,
        "q4_items": q4_items,
        "all_items": all_items,
        "done_items": done_items,
        "status_filter": status_filter,
        "category_filter": category_filter,
        "today": today.isoformat(),
        "categories": TodoItem.CATEGORY_CHOICES,
        "quadrants": TodoItem.QUADRANT_CHOICES,
    }
    return render(request, "todos/todo_list.html", context)


@require_POST
def todo_create(request):
    title = request.POST.get("title", "")
    quadrant = request.POST.get("quadrant", "q1")
    category = request.POST.get("category", "other")
    due_date = request.POST.get("due_date", "")
    note = request.POST.get("note", "")

    item, error = create_todo(title, quadrant, category, due_date, note)
    if error:
        messages.error(request, f"新增失败：{error}")
    else:
        messages.success(request, "待办已添加")
    return redirect("todo_list")


@require_POST
def todo_update(request):
    item_id = request.POST.get("item_id", "")
    title = request.POST.get("title", "")
    quadrant = request.POST.get("quadrant", "q1")
    category = request.POST.get("category", "other")
    due_date = request.POST.get("due_date", "")
    note = request.POST.get("note", "")

    ok = update_todo(item_id, title, quadrant, category, due_date, note)
    if not ok:
        messages.error(request, "更新失败：未找到待办项")
        return HttpResponseBadRequest("未找到待办项")
    messages.success(request, "待办已更新")
    return redirect("todo_list")


@require_POST
def todo_toggle(request):
    item_id = request.POST.get("item_id", "")
    ok = toggle_todo(item_id)
    if not ok:
        messages.error(request, "操作失败：未找到待办项")
        return HttpResponseBadRequest("未找到待办项")
    messages.success(request, "状态已更新")
    return redirect("todo_list")


@require_POST
def todo_delete(request):
    item_id = request.POST.get("item_id", "")
    delete_todo(item_id)
    messages.success(request, "待办已删除")
    return redirect("todo_list")


@require_POST
def todo_move(request):
    item_id = request.POST.get("item_id", "")
    quadrant = request.POST.get("quadrant", "")
    ok = move_quadrant(item_id, quadrant)
    if not ok:
        messages.error(request, "移动失败")
        return HttpResponseBadRequest("移动失败")
    messages.success(request, "已移动到新象限")
    return redirect("todo_list")
