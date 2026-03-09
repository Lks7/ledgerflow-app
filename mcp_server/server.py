import json
import os
import sys
import traceback
from calendar import monthrange
from datetime import date
from typing import Any, Callable

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

import django  # noqa: E402

django.setup()

from analytics.services import (  # noqa: E402
    monthly_summary,
    summary_for_period,
    yearly_summary,
)
from django.db.models import Sum  # noqa: E402
from ledger.services import (  # noqa: E402
    create_journal,
    delete_journal,
    get_accounts,
    get_categories,
    get_journal,
    list_all_tags,
    list_journals,
    update_journal,
)
from ledger.models import Category, JournalEntry  # noqa: E402
from lists.services import (  # noqa: E402
    add_item,
    delete_item,
    list_items,
    pending_summary,
    update_item,
    update_status,
)
from storage.services import run_with_idempotency  # noqa: E402


def _ok(result: Any) -> dict:
    return {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]
    }


def _err(message: str) -> dict:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"ok": False, "error": message}, ensure_ascii=False),
            }
        ],
        "isError": True,
    }


def _required(args: dict, key: str) -> Any:
    value = args.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"missing required argument: {key}")
    return value


def tool_ledger_get_accounts(_args: dict) -> dict:
    return {"ok": True, "accounts": get_accounts()}


def tool_ledger_get_categories(_args: dict) -> dict:
    return {"ok": True, "categories": get_categories()}


def tool_ledger_list_tags(_args: dict) -> dict:
    return {"ok": True, "tags": list_all_tags()}


def tool_ledger_list_journals(args: dict) -> dict:
    month = (args.get("month") or "").strip()
    tag = (args.get("tag") or "").strip()
    account_id = (args.get("account_id") or "").strip()
    category_id = (args.get("category_id") or "").strip()

    rows = list_journals(month=month, tag=tag)

    if account_id:
        rows = [
            j
            for j in rows
            if any(
                (e.get("account_id") or "") == account_id
                for e in (j.get("entries") or [])
            )
            or any(
                (t.get("from_account_id") or "") == account_id
                or (t.get("to_account_id") or "") == account_id
                for t in (j.get("transfers") or [])
            )
        ]

    if category_id:
        rows = [
            j
            for j in rows
            if any(
                (e.get("category_id") or "") == category_id
                for e in (j.get("entries") or [])
            )
        ]

    return {"ok": True, "journals": rows}


def tool_ledger_get_journal(args: dict) -> dict:
    month = _required(args, "month")
    journal_id = _required(args, "journal_id")
    j = get_journal(month, journal_id)
    if not j:
        return {"ok": False, "error": "journal not found"}
    return {"ok": True, "journal": j}


def tool_ledger_create_journal(args: dict) -> dict:
    idempotency_key = (args.get("idempotency_key") or "").strip()
    date = _required(args, "date")
    description = _required(args, "description")
    source = args.get("source", "mcp")
    tags = args.get("tags", "")
    entries = args.get("entries", [])
    transfer_lines = args.get("transfer_lines", [])

    def _run() -> dict:
        journal, error = create_journal(
            date=date,
            description=description,
            source=source,
            tags=tags,
            entries=entries,
            transfer_lines=transfer_lines,
        )
        if error:
            return {"ok": False, "error": error}
        return {"ok": True, "journal": journal}

    if idempotency_key:
        return run_with_idempotency(
            tool_name="ledger.create_journal",
            idempotency_key=idempotency_key,
            args_for_hash={
                "date": date,
                "description": description,
                "source": source,
                "tags": tags,
                "entries": entries,
                "transfer_lines": transfer_lines,
            },
            runner=_run,
        )

    return _run()


def tool_ledger_update_journal(args: dict) -> dict:
    month = _required(args, "month")
    journal_id = _required(args, "journal_id")
    date = _required(args, "date")
    description = _required(args, "description")
    source = args.get("source", "mcp")
    tags = args.get("tags", "")
    entries = args.get("entries", [])
    transfer_lines = args.get("transfer_lines", [])

    journal, error = update_journal(
        month=month,
        journal_id=journal_id,
        date=date,
        description=description,
        source=source,
        tags=tags,
        entries=entries,
        transfer_lines=transfer_lines,
    )
    if error:
        return {"ok": False, "error": error}
    return {"ok": True, "journal": journal}


def tool_ledger_delete_journal(args: dict) -> dict:
    month = _required(args, "month")
    journal_id = _required(args, "journal_id")
    confirm = bool(args.get("confirm", False))
    if not confirm:
        return {"ok": False, "error": "confirm=true required for delete"}
    deleted = delete_journal(month=month, journal_id=journal_id)
    return {"ok": bool(deleted), "deleted": bool(deleted)}


def tool_shopping_list_items(args: dict) -> dict:
    status = (args.get("status") or "").strip()
    return {"ok": True, "items": list_items(status=status)}


def tool_shopping_add_item(args: dict) -> dict:
    idempotency_key = (args.get("idempotency_key") or "").strip()
    name = _required(args, "name")
    qty = args.get("qty", 1)
    est_price = args.get("est_price", 0)
    actual_price = args.get("actual_price", 0)
    priority = args.get("priority", "normal")
    planned_date = args.get("planned_date", "")
    platform = args.get("platform", "")
    note = args.get("note", "")

    def _run() -> dict:
        item = add_item(
            name=name,
            qty=qty,
            est_price=est_price,
            actual_price=actual_price,
            priority=priority,
            planned_date=planned_date,
            platform=platform,
            note=note,
        )
        return {"ok": True, "item": item}

    if idempotency_key:
        return run_with_idempotency(
            tool_name="shopping.add_item",
            idempotency_key=idempotency_key,
            args_for_hash={
                "name": name,
                "qty": qty,
                "est_price": est_price,
                "actual_price": actual_price,
                "priority": priority,
                "planned_date": planned_date,
                "platform": platform,
                "note": note,
            },
            runner=_run,
        )

    return _run()


def tool_shopping_update_item(args: dict) -> dict:
    item_id = _required(args, "item_id")
    ok = update_item(
        item_id=item_id,
        name=args.get("name", ""),
        qty=args.get("qty", 1),
        est_price=args.get("est_price", 0),
        actual_price=args.get("actual_price", 0),
        priority=args.get("priority", "normal"),
        planned_date=args.get("planned_date", ""),
        platform=args.get("platform", ""),
        note=args.get("note", ""),
    )
    return {"ok": bool(ok)}


def tool_shopping_update_status(args: dict) -> dict:
    item_id = _required(args, "item_id")
    status = _required(args, "status")
    ok = update_status(item_id=item_id, status=status)
    return {"ok": bool(ok)}


def tool_shopping_delete_item(args: dict) -> dict:
    item_id = _required(args, "item_id")
    confirm = bool(args.get("confirm", False))
    if not confirm:
        return {"ok": False, "error": "confirm=true required for delete"}
    ok = delete_item(item_id=item_id)
    return {"ok": bool(ok)}


def tool_shopping_pending_summary(_args: dict) -> dict:
    return {"ok": True, "summary": pending_summary()}


def tool_report_monthly(args: dict) -> dict:
    month = _required(args, "month")
    return {"ok": True, "summary": monthly_summary(month)}


def tool_report_period(args: dict) -> dict:
    period = (args.get("period") or "month").strip()
    if period not in {"day", "week", "month", "year"}:
        raise ValueError("period must be one of day/week/month/year")
    return {"ok": True, "summary": summary_for_period(period)}


def tool_report_yearly(args: dict) -> dict:
    year = _required(args, "year")
    return {"ok": True, "summary": yearly_summary(year)}


def tool_budget_center_summary(args: dict) -> dict:
    scope = (args.get("scope") or "month").strip()
    if scope not in {"month", "year"}:
        raise ValueError("scope must be one of month/year")

    month = (args.get("month") or date.today().strftime("%Y-%m")).strip()
    year = (args.get("year") or date.today().strftime("%Y")).strip()

    if scope == "month":
        summary = monthly_summary(month)
        actual_by_cat = {
            (item.get("category_id") or ""): float(item.get("amount") or 0)
            for item in summary.get("categories", [])
        }
        try:
            trend_year = int(month.split("-")[0])
        except Exception:
            trend_year = date.today().year
    else:
        agg = (
            JournalEntry.objects.filter(
                journal__date__startswith=year,
                account__type="expense",
            )
            .values("category_id")
            .annotate(total=Sum("debit"))
        )
        actual_by_cat = {
            (r.get("category_id") or ""): float(r.get("total") or 0) for r in agg
        }
        try:
            trend_year = int(year)
        except Exception:
            trend_year = date.today().year

    rows = []
    total_budget = 0.0
    total_actual = 0.0

    for cat in Category.objects.order_by("group", "name"):
        monthly_budget = float(cat.budget_monthly or 0)
        budget = monthly_budget if scope == "month" else monthly_budget * 12
        actual = actual_by_cat.get(cat.id, 0.0)
        remain = budget - actual
        usage_pct = (actual / budget * 100.0) if budget > 0 else 0.0

        if budget <= 0:
            status = "未设预算"
        elif usage_pct >= 100:
            status = "超预算"
        elif usage_pct >= 80:
            status = "预警"
        else:
            status = "正常"

        rows.append(
            {
                "id": cat.id,
                "name": cat.name,
                "group": cat.group,
                "budget": round(budget, 2),
                "actual": round(actual, 2),
                "remain": round(remain, 2),
                "usage_pct": round(usage_pct, 1),
                "status": status,
            }
        )
        total_budget += budget
        total_actual += actual

    rows.sort(
        key=lambda x: (x["status"] != "超预算", x["status"] != "预警", -x["actual"])
    )

    monthly_budget_total = float(
        sum(float(c.budget_monthly or 0) for c in Category.objects.all())
    )
    month_actual_map = {
        int(r["journal__date__month"]): float(r["total"] or 0)
        for r in JournalEntry.objects.filter(
            journal__date__year=trend_year,
            account__type="expense",
        )
        .values("journal__date__month")
        .annotate(total=Sum("debit"))
    }
    trend = [
        {
            "month": f"{m:02d}",
            "budget": round(monthly_budget_total, 2),
            "actual": round(month_actual_map.get(m, 0.0), 2),
            "diff": round(monthly_budget_total - month_actual_map.get(m, 0.0), 2),
        }
        for m in range(1, 13)
    ]

    return {
        "ok": True,
        "scope": scope,
        "month": month,
        "year": year,
        "trend_year": trend_year,
        "period_label": "月预算" if scope == "month" else "年预算",
        "total_budget": round(total_budget, 2),
        "total_actual": round(total_actual, 2),
        "total_remain": round(total_budget - total_actual, 2),
        "total_usage_pct": round((total_actual / total_budget * 100.0), 1)
        if total_budget > 0
        else 0.0,
        "warnings": [r for r in rows if r["status"] in {"超预算", "预警"}],
        "rows": rows,
        "trend": trend,
    }


def _add_months(ym: str, offset: int) -> str:
    y, m = map(int, ym.split("-"))
    m += offset
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}"


def _date_with_day(ym: str, day: int) -> str:
    y, m = map(int, ym.split("-"))
    d = max(1, min(day, monthrange(y, m)[1]))
    return f"{y:04d}-{m:02d}-{d:02d}"


def tool_ledger_create_rent_template(args: dict) -> dict:
    idempotency_key = (args.get("idempotency_key") or "").strip()

    pay_date = _required(args, "pay_date")
    start_month = _required(args, "start_month")
    from_account_id = _required(args, "from_account_id")
    prepaid_account_id = _required(args, "prepaid_account_id")
    deposit_account_id = (args.get("deposit_account_id") or "").strip()
    category_id = (args.get("category_id") or "").strip()
    tags = (args.get("tags") or "房租").strip()
    note = (args.get("note") or "").strip()

    monthly_rent = float(args.get("monthly_rent") or 0)
    months_count = int(args.get("months_count") or 3)
    deposit_amount = float(args.get("deposit_amount") or 0)

    if monthly_rent <= 0 or months_count <= 0:
        return {"ok": False, "error": "monthly_rent and months_count must be > 0"}
    if deposit_amount > 0 and not deposit_account_id:
        return {
            "ok": False,
            "error": "deposit_account_id is required when deposit_amount > 0",
        }

    pay_day = int(pay_date.split("-")[-1])
    total_prepaid = round(monthly_rent * months_count, 2)
    total_amount = round(total_prepaid + deposit_amount, 2)

    initial_entries = [
        {
            "account_id": prepaid_account_id,
            "category_id": "",
            "debit": f"{total_prepaid:.2f}",
            "credit": "0.00",
            "currency": "CNY",
            "note": "房租预付",
        },
        {
            "account_id": from_account_id,
            "category_id": "",
            "debit": "0.00",
            "credit": f"{total_amount:.2f}",
            "currency": "CNY",
            "note": "房租付款",
        },
    ]
    if deposit_amount > 0:
        initial_entries.insert(
            1,
            {
                "account_id": deposit_account_id,
                "category_id": "",
                "debit": f"{deposit_amount:.2f}",
                "credit": "0.00",
                "currency": "CNY",
                "note": "租房押金",
            },
        )

    def _run() -> dict:
        created = []
        j0, err = create_journal(
            date=pay_date,
            description=f"房租付款（押{int(deposit_amount // monthly_rent) if monthly_rent else 0}付{months_count}）",
            source="template_rent",
            tags=f"{tags},房租模板",
            entries=initial_entries,
            transfer_lines=[],
        )
        if err:
            return {"ok": False, "error": err}
        created.append(j0.get("id"))

        for i in range(months_count):
            ym = _add_months(start_month, i)
            d = _date_with_day(ym, pay_day)
            entries = [
                {
                    "account_id": "expense",
                    "category_id": category_id,
                    "debit": f"{monthly_rent:.2f}",
                    "credit": "0.00",
                    "currency": "CNY",
                    "note": f"房租分摊 {ym} {note}".strip(),
                },
                {
                    "account_id": prepaid_account_id,
                    "category_id": "",
                    "debit": "0.00",
                    "credit": f"{monthly_rent:.2f}",
                    "currency": "CNY",
                    "note": f"房租分摊 {ym}",
                },
            ]
            jx, errx = create_journal(
                date=d,
                description=f"房租分摊 {ym}",
                source="template_rent",
                tags=f"{tags},房租分摊",
                entries=entries,
                transfer_lines=[],
            )
            if errx:
                return {"ok": False, "error": errx, "created_ids": created}
            created.append(jx.get("id"))

        return {"ok": True, "created_count": len(created), "journal_ids": created}

    if idempotency_key:
        return run_with_idempotency(
            tool_name="ledger.create_rent_template",
            idempotency_key=idempotency_key,
            args_for_hash={
                "pay_date": pay_date,
                "start_month": start_month,
                "from_account_id": from_account_id,
                "prepaid_account_id": prepaid_account_id,
                "deposit_account_id": deposit_account_id,
                "category_id": category_id,
                "tags": tags,
                "note": note,
                "monthly_rent": monthly_rent,
                "months_count": months_count,
                "deposit_amount": deposit_amount,
            },
            runner=_run,
        )

    return _run()


TOOLS: dict[str, tuple[dict, Callable[[dict], dict]]] = {
    "ledger.get_accounts": (
        {
            "name": "ledger.get_accounts",
            "description": "Get all accounts",
            "inputSchema": {"type": "object", "properties": {}},
        },
        tool_ledger_get_accounts,
    ),
    "ledger.get_categories": (
        {
            "name": "ledger.get_categories",
            "description": "Get all categories",
            "inputSchema": {"type": "object", "properties": {}},
        },
        tool_ledger_get_categories,
    ),
    "ledger.list_tags": (
        {
            "name": "ledger.list_tags",
            "description": "Get all tags with usage count",
            "inputSchema": {"type": "object", "properties": {}},
        },
        tool_ledger_list_tags,
    ),
    "ledger.list_journals": (
        {
            "name": "ledger.list_journals",
            "description": "List journals with optional filters",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "month": {
                        "type": "string",
                        "description": "YYYY-MM; empty for all",
                    },
                    "tag": {"type": "string"},
                    "account_id": {"type": "string"},
                    "category_id": {"type": "string"},
                },
            },
        },
        tool_ledger_list_journals,
    ),
    "ledger.get_journal": (
        {
            "name": "ledger.get_journal",
            "description": "Get a single journal by id",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "month": {"type": "string"},
                    "journal_id": {"type": "string"},
                },
                "required": ["month", "journal_id"],
            },
        },
        tool_ledger_get_journal,
    ),
    "ledger.create_journal": (
        {
            "name": "ledger.create_journal",
            "description": "Create a new journal entry",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "description": {"type": "string"},
                    "source": {"type": "string"},
                    "tags": {"type": "string"},
                    "idempotency_key": {"type": "string"},
                    "entries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "account_id": {"type": "string"},
                                "category_id": {"type": "string"},
                                "debit": {"type": "string"},
                                "credit": {"type": "string"},
                                "currency": {"type": "string"},
                                "note": {"type": "string"},
                            },
                            "required": ["account_id", "debit", "credit"],
                        },
                    },
                    "transfer_lines": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from_account_id": {"type": "string"},
                                "to_account_id": {"type": "string"},
                                "amount": {"type": "string"},
                                "currency": {"type": "string"},
                                "note": {"type": "string"},
                            },
                            "required": ["from_account_id", "to_account_id", "amount"],
                        },
                    },
                },
                "required": ["date", "description", "entries"],
            },
        },
        tool_ledger_create_journal,
    ),
    "ledger.update_journal": (
        {
            "name": "ledger.update_journal",
            "description": "Update an existing journal",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "month": {"type": "string"},
                    "journal_id": {"type": "string"},
                    "date": {"type": "string"},
                    "description": {"type": "string"},
                    "source": {"type": "string"},
                    "tags": {"type": "string"},
                    "entries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "account_id": {"type": "string"},
                                "category_id": {"type": "string"},
                                "debit": {"type": "string"},
                                "credit": {"type": "string"},
                                "currency": {"type": "string"},
                                "note": {"type": "string"},
                            },
                            "required": ["account_id", "debit", "credit"],
                        },
                    },
                    "transfer_lines": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from_account_id": {"type": "string"},
                                "to_account_id": {"type": "string"},
                                "amount": {"type": "string"},
                                "currency": {"type": "string"},
                                "note": {"type": "string"},
                            },
                            "required": ["from_account_id", "to_account_id", "amount"],
                        },
                    },
                },
                "required": ["month", "journal_id", "date", "description", "entries"],
            },
        },
        tool_ledger_update_journal,
    ),
    "ledger.delete_journal": (
        {
            "name": "ledger.delete_journal",
            "description": "Delete a journal (confirm=true required)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "month": {"type": "string"},
                    "journal_id": {"type": "string"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["month", "journal_id", "confirm"],
            },
        },
        tool_ledger_delete_journal,
    ),
    "shopping.list_items": (
        {
            "name": "shopping.list_items",
            "description": "List shopping items",
            "inputSchema": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
            },
        },
        tool_shopping_list_items,
    ),
    "shopping.add_item": (
        {
            "name": "shopping.add_item",
            "description": "Add shopping item",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "idempotency_key": {"type": "string"},
                    "qty": {"type": "integer"},
                    "est_price": {"type": "number"},
                    "actual_price": {"type": "number"},
                    "priority": {"type": "string"},
                    "planned_date": {"type": "string"},
                    "platform": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["name"],
            },
        },
        tool_shopping_add_item,
    ),
    "shopping.update_item": (
        {
            "name": "shopping.update_item",
            "description": "Update shopping item",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "name": {"type": "string"},
                    "qty": {"type": "integer"},
                    "est_price": {"type": "number"},
                    "actual_price": {"type": "number"},
                    "priority": {"type": "string"},
                    "planned_date": {"type": "string"},
                    "platform": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["item_id"],
            },
        },
        tool_shopping_update_item,
    ),
    "shopping.update_status": (
        {
            "name": "shopping.update_status",
            "description": "Update shopping item status",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "status": {"type": "string"},
                },
                "required": ["item_id", "status"],
            },
        },
        tool_shopping_update_status,
    ),
    "shopping.delete_item": (
        {
            "name": "shopping.delete_item",
            "description": "Delete shopping item (confirm=true required)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["item_id", "confirm"],
            },
        },
        tool_shopping_delete_item,
    ),
    "shopping.pending_summary": (
        {
            "name": "shopping.pending_summary",
            "description": "Get pending shopping summary",
            "inputSchema": {"type": "object", "properties": {}},
        },
        tool_shopping_pending_summary,
    ),
    "report.monthly_summary": (
        {
            "name": "report.monthly_summary",
            "description": "Get monthly financial summary",
            "inputSchema": {
                "type": "object",
                "properties": {"month": {"type": "string", "description": "YYYY-MM"}},
                "required": ["month"],
            },
        },
        tool_report_monthly,
    ),
    "report.period_summary": (
        {
            "name": "report.period_summary",
            "description": "Get period summary by day/week/month/year",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["day", "week", "month", "year"],
                    }
                },
            },
        },
        tool_report_period,
    ),
    "report.yearly_summary": (
        {
            "name": "report.yearly_summary",
            "description": "Get yearly financial summary",
            "inputSchema": {
                "type": "object",
                "properties": {"year": {"type": "string", "description": "YYYY"}},
                "required": ["year"],
            },
        },
        tool_report_yearly,
    ),
    "report.budget_center_summary": (
        {
            "name": "report.budget_center_summary",
            "description": "Get budget center summary with monthly trend",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "enum": ["month", "year"]},
                    "month": {"type": "string", "description": "YYYY-MM"},
                    "year": {"type": "string", "description": "YYYY"},
                },
            },
        },
        tool_budget_center_summary,
    ),
    "ledger.create_rent_template": (
        {
            "name": "ledger.create_rent_template",
            "description": "Create rent journals for deposit and monthly amortization",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "idempotency_key": {"type": "string"},
                    "pay_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "start_month": {"type": "string", "description": "YYYY-MM"},
                    "from_account_id": {"type": "string"},
                    "prepaid_account_id": {"type": "string"},
                    "deposit_account_id": {"type": "string"},
                    "category_id": {"type": "string"},
                    "tags": {"type": "string"},
                    "note": {"type": "string"},
                    "monthly_rent": {"type": "number"},
                    "months_count": {"type": "integer"},
                    "deposit_amount": {"type": "number"},
                },
                "required": [
                    "pay_date",
                    "start_month",
                    "from_account_id",
                    "prepaid_account_id",
                    "monthly_rent",
                    "months_count",
                ],
            },
        },
        tool_ledger_create_rent_template,
    ),
}

# Some model providers (e.g. DeepSeek function calling) require tool names to
# match ^[a-zA-Z0-9_-]+$ and reject dots. Keep internal dotted names, but
# expose/accept transport-safe aliases with dots replaced by underscores.
TOOL_ALIASES: dict[str, str] = {name.replace(".", "_"): name for name in TOOLS.keys()}


def _handle_request(req: dict) -> dict | None:
    method = req.get("method")
    req_id = req.get("id")

    if method == "notifications/initialized":
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "ledgerflow-mcp", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        }

    if method == "tools/list":
        tool_list = []
        for internal_name, (meta, _fn) in TOOLS.items():
            safe_name = internal_name.replace(".", "_")
            item = dict(meta)
            item["name"] = safe_name
            tool_list.append(item)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tool_list},
        }

    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        internal_name = name
        if internal_name not in TOOLS:
            internal_name = TOOL_ALIASES.get(str(name), "")

        if internal_name not in TOOLS:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": _err(f"unknown tool: {name}"),
            }
        _meta, fn = TOOLS[internal_name]
        try:
            result = fn(arguments)
            return {"jsonrpc": "2.0", "id": req_id, "result": _ok(result)}
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": _err(f"{type(exc).__name__}: {exc}"),
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def handle_jsonrpc_request(req: dict) -> dict | None:
    """Public handler for JSON-RPC MCP requests.

    This can be reused by stdio mode and HTTP mode.
    """
    return _handle_request(req)


def _read_exact(buffer, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining > 0:
        chunk = buffer.read(remaining)
        if not chunk:
            raise EOFError("unexpected EOF while reading message body")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_message() -> tuple[bool, dict | None]:
    """Read one MCP message.

    Returns:
      (False, None) on EOF
      (True, None) for ignorable blank lines
      (True, dict) for a parsed JSON-RPC request
    """

    # Prefer binary streams so Content-Length is interpreted in bytes.
    buffer = sys.stdin.buffer

    first = buffer.readline()
    if first == b"":
        return False, None

    first_strip = first.strip()
    if not first_strip:
        return True, None

    if first_strip.lower().startswith(b"content-length:"):
        try:
            length = int(first_strip.split(b":", 1)[1].strip())
        except Exception:
            raise ValueError("invalid Content-Length header")

        # consume remaining headers until blank line
        while True:
            h = buffer.readline()
            if h == b"":
                return False, None
            if h in (b"\n", b"\r\n"):
                break

        payload = _read_exact(buffer, length)
        return True, json.loads(payload.decode("utf-8"))

    # Fallback: one-line JSON (for manual testing)
    return True, json.loads(first_strip.decode("utf-8"))


def _write_message(resp: dict) -> None:
    payload = json.dumps(resp, ensure_ascii=False)
    framed = f"Content-Length: {len(payload.encode('utf-8'))}\r\n\r\n{payload}"
    sys.stdout.buffer.write(framed.encode("utf-8"))
    sys.stdout.buffer.flush()


def run_stdio() -> None:
    while True:
        has_message, req = _read_message()
        if not has_message:
            break
        if req is None:
            continue
        try:
            resp = _handle_request(req)
            if resp is not None:
                _write_message(resp)
        except Exception:
            err = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": "internal error",
                    "data": traceback.format_exc(),
                },
            }
            _write_message(err)


if __name__ == "__main__":
    run_stdio()
