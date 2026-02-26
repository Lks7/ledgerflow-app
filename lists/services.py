import json
import re
import uuid
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum, F
from google import genai

from .models import ShoppingItem


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
