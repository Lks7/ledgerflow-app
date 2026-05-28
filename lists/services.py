import json
import re
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum, F
from google import genai

from .models import ShoppingItem, SubscriptionService


def _date_str(val) -> str:
    """将 date / datetime / str / None 统一转为 ISO 字符串。"""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    return val.isoformat()


def _subscription_progress(item: SubscriptionService) -> dict:
    """计算订阅到期进度信息（供模板渲染进度条）。"""
    today = date.today()
    renewal = item.next_renewal_date  # date 对象
    if not renewal:
        return {"progress_pct": 0, "days_left": 0, "progress_color": "red", "cycle_days": 0}

    # 推算周期天数
    if item.billing_cycle == "monthly":
        cycle_days = 30
    elif item.billing_cycle == "quarterly":
        cycle_days = 90
    elif item.billing_cycle == "yearly":
        cycle_days = 365
    else:
        cycle_days = max(1, int(item.custom_days or 30))

    # 起点：优先用 start_date，否则从 next_renewal_date 反推
    if item.start_date:
        start = item.start_date
    else:
        start = renewal - timedelta(days=cycle_days)

    days_left = (renewal - today).days
    total_days = (renewal - start).days or 1
    elapsed_days = (today - start).days
    # 限制在 0~100 之间
    progress_pct = max(0, min(100, int(elapsed_days / total_days * 100)))

    if days_left >= 14:
        color = "green"
    elif days_left >= 7:
        color = "yellow"
    else:
        color = "red"

    return {
        "progress_pct": progress_pct,
        "days_left": max(0, days_left),
        "progress_color": color,
        "cycle_days": cycle_days,
    }


def _subscription_to_dict(item: SubscriptionService) -> dict:
    progress = _subscription_progress(item)
    return {
        "id": item.id,
        "name": item.name,
        "service_type": item.service_type,
        "billing_cycle": item.billing_cycle,
        "custom_days": item.custom_days,
        "price": float(item.price or 0),
        "start_date": _date_str(item.start_date),
        "next_renewal_date": _date_str(item.next_renewal_date),
        "expiry_date": _date_str(item.expiry_date),
        "status": item.status,
        "note": item.note,
        "created_at": _date_str(item.created_at),
        "updated_at": _date_str(item.updated_at),
        # 进度条数据
        "progress_pct": progress["progress_pct"],
        "days_left": progress["days_left"],
        "progress_color": progress["progress_color"],
        "cycle_days": progress["cycle_days"],
    }


def list_subscriptions(status: str = ""):
    qs = SubscriptionService.objects.all()
    if status:
        qs = qs.filter(status=status)
    return [_subscription_to_dict(x) for x in qs]


def create_subscription(
    name,
    service_type,
    billing_cycle,
    custom_days,
    price,
    start_date,
    next_renewal_date,
    expiry_date="",
    note="",
):
    item = SubscriptionService.objects.create(
        id=str(uuid.uuid4()),
        name=(name or "").strip(),
        service_type=(service_type or "").strip(),
        billing_cycle=billing_cycle or "monthly",
        custom_days=int(custom_days or 30),
        price=Decimal(str(price or "0")),
        start_date=(start_date or None),
        next_renewal_date=(next_renewal_date or None),
        expiry_date=(expiry_date or None),
        note=note or "",
    )
    item.refresh_from_db()
    return _subscription_to_dict(item)


def update_subscription(
    item_id: str,
    name,
    service_type,
    billing_cycle,
    custom_days,
    price,
    start_date,
    next_renewal_date,
    expiry_date="",
    status="active",
    note="",
):
    try:
        item = SubscriptionService.objects.get(id=item_id)
    except SubscriptionService.DoesNotExist:
        return False
    item.name = (name or "").strip()
    item.service_type = (service_type or "").strip()
    item.billing_cycle = billing_cycle or "monthly"
    item.custom_days = int(custom_days or 30)
    item.price = Decimal(str(price or "0"))
    item.start_date = start_date or None
    item.next_renewal_date = next_renewal_date
    item.expiry_date = expiry_date or None
    item.status = status or "active"
    item.note = note or ""
    item.save()
    item.refresh_from_db()
    return True


def delete_subscription(item_id: str) -> bool:
    try:
        SubscriptionService.objects.get(id=item_id).delete()
        return True
    except SubscriptionService.DoesNotExist:
        return False


def renew_subscription(item_id: str):
    from datetime import timedelta

    try:
        item = SubscriptionService.objects.get(id=item_id)
    except SubscriptionService.DoesNotExist:
        return False
    current = item.next_renewal_date
    if item.billing_cycle == "monthly":
        days = 30
    elif item.billing_cycle == "quarterly":
        days = 90
    elif item.billing_cycle == "yearly":
        days = 365
    else:
        days = max(1, int(item.custom_days or 30))
    item.next_renewal_date = current + timedelta(days=days)
    item.save(update_fields=["next_renewal_date", "updated_at"])
    return True


def subscription_summary() -> dict:
    items = SubscriptionService.objects.filter(status="active")
    return {
        "count": items.count(),
        "total_price": round(float(sum(float(x.price or 0) for x in items)), 2),
    }


def _item_to_dict(item):
    qty = int(item.qty or 1)
    est_price = float(item.est_price or 0)
    actual_price = float(item.actual_price or 0)
    budget_total = est_price * qty
    actual_total = actual_price * qty
    return {
        "id": item.id,
        "name": item.name,
        "qty": qty,
        "est_price": est_price,
        "actual_price": actual_price,
        "budget_total": round(budget_total, 2),
        "actual_total": round(actual_total, 2),
        "variance_total": round(actual_total - budget_total, 2),
        "priority": item.priority,
        "status": item.status,
        "planned_date": item.planned_date,
        "platform": item.platform,
        "note": item.note,
        "created_at": item.created_at.isoformat() if item.created_at else "",
        "updated_at": item.updated_at.isoformat() if item.updated_at else "",
    }


def list_items(status: str = ""):
    qs = ShoppingItem.objects.all()
    if status:
        qs = qs.filter(status=status)

    items = [_item_to_dict(x) for x in qs]
    priority_order = {"high": 0, "normal": 1, "low": 2}
    return sorted(
        items,
        key=lambda x: (
            0 if x.get("status") == "pending" else 1,
            priority_order.get(x.get("priority", "normal"), 1),
            x.get("created_at", ""),
        ),
    )


def add_item(
    name,
    qty,
    est_price,
    actual_price,
    priority,
    planned_date,
    platform="",
    note="",
):
    item = ShoppingItem.objects.create(
        id=str(uuid.uuid4()),
        name=name,
        qty=int(qty or 1),
        est_price=Decimal(str(est_price or "0")),
        actual_price=Decimal(str(actual_price or "0")),
        priority=priority or "normal",
        status="pending",
        planned_date=planned_date or "",
        platform=(platform or "").strip(),
        note=note or "",
    )
    return _item_to_dict(item)


def update_item(
    item_id: str,
    name,
    qty,
    est_price,
    actual_price,
    priority,
    planned_date,
    platform="",
    note="",
):
    try:
        item = ShoppingItem.objects.get(id=item_id)
    except ShoppingItem.DoesNotExist:
        return False

    item.name = name
    item.qty = int(qty or 1)
    item.est_price = Decimal(str(est_price or "0"))
    item.actual_price = Decimal(str(actual_price or "0"))
    item.priority = priority or "normal"
    item.planned_date = planned_date or ""
    item.platform = (platform or "").strip()
    item.note = note or ""
    item.save()
    return True


def update_status(item_id: str, status: str):
    try:
        item = ShoppingItem.objects.get(id=item_id)
        item.status = status
        item.save()
        return True
    except ShoppingItem.DoesNotExist:
        return False


def delete_item(item_id: str) -> bool:
    try:
        ShoppingItem.objects.get(id=item_id).delete()
        return True
    except ShoppingItem.DoesNotExist:
        return False


def get_item(item_id: str):
    try:
        item = ShoppingItem.objects.get(id=item_id)
        return _item_to_dict(item)
    except ShoppingItem.DoesNotExist:
        return None


def pending_summary():
    qs = ShoppingItem.objects.filter(status="pending")
    count = qs.count()
    aggr = qs.aggregate(
        budget_total=Sum(F("qty") * F("est_price")),
        actual_total=Sum(F("qty") * F("actual_price")),
    )
    total_budget = aggr["budget_total"] or Decimal("0.00")
    total_actual = aggr["actual_total"] or Decimal("0.00")
    variance = total_actual - total_budget

    return {
        "count": count,
        "total_budget": round(float(total_budget), 2),
        "total_actual": round(float(total_actual), 2),
        "variance": round(float(variance), 2),
    }


def ai_analyze_items(items: list) -> dict:
    """Call Gemini to analyze shopping list items for necessity and priority."""
    if not items:
        return {
            "items": [],
            "summary": "清单为空，暂无分析内容。",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }

    if not getattr(settings, "GOOGLE_API_KEY", ""):
        return _rule_based_analyze(items)

    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        items_text = "\n".join(
            [
                f"- {x.get('name')} x{x.get('qty', 1)} 单价¥{x.get('est_price', 0):.2f} 优先级:{x.get('priority', 'normal')} 备注:{x.get('note', '')}"
                for x in items
            ]
        )
        prompt = (
            "你是一位理性消费顾问。请分析以下购物清单，给出每项的必要性和购买建议。\n"
            "严格返回合法 JSON（不要有其他文字），格式：\n"
            "{\n"
            '  "items": [\n'
            '    {"id": "<item_id>", "verdict": "必要|可选|建议跳过", "reason": "一句话说明(≤30字)", "score": 1-10}\n'
            "    ...\n"
            "  ],\n"
            '  "summary": "总结建议(≤80字)"\n'
            "}\n\n"
            "购物清单：\n"
            + "\n".join(
                [
                    f"id:{x.get('id')} 名称:{x.get('name')} 数量:{x.get('qty', 1)} 单价:¥{x.get('est_price', 0):.2f} 优先级:{x.get('priority', 'normal')} 备注:{x.get('note', '')}"
                    for x in items
                ]
            )
        )
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL, contents=prompt
        )
        text = (response.text or "").strip()
        text_clean = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        parsed = json.loads(text_clean)
        parsed["generated_at"] = datetime.now().isoformat(timespec="seconds")
        parsed["mode"] = "gemini"
        return parsed
    except Exception:
        return _rule_based_analyze(items)


def _rule_based_analyze(items: list) -> dict:
    results = []
    for item in items:
        priority = item.get("priority", "normal")
        price = item.get("est_price", 0) * item.get("qty", 1)
        if priority == "high":
            verdict, reason, score = "必要", "高优先级，建议优先购买", 9
        elif priority == "low" and price > 200:
            verdict, reason, score = "建议跳过", "低优先级且金额较高，建议延后", 3
        elif priority == "low":
            verdict, reason, score = "可选", "低优先级，非紧急可延后购买", 5
        else:
            verdict, reason, score = "可选", "中等优先级，评估需求后决定", 6
        results.append(
            {
                "id": item.get("id"),
                "verdict": verdict,
                "reason": reason,
                "score": score,
            }
        )
    must_buy = [r for r in results if r["verdict"] == "必要"]
    skip = [r for r in results if r["verdict"] == "建议跳过"]
    summary = f"建议优先购买 {len(must_buy)} 件必要物品"
    if skip:
        summary += f"，可考虑跳过 {len(skip)} 件低必要性物品"
    summary += "。"
    return {
        "items": results,
        "summary": summary,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "rules",
    }
