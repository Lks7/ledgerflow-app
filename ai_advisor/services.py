import json
import re
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
import httpx
from google import genai

from analytics.services import monthly_summary
from ledger.services import create_journal


def _to_decimal(v) -> Decimal:
    try:
        return Decimal(str(v or "0"))
    except Exception:
        return Decimal("0")


def _account_net_change(account: dict, journals: list) -> Decimal:
    account_id = account.get("id")
    account_type = account.get("type")
    net = Decimal("0")
    for j in journals:
        for e in j.get("entries", []):
            if e.get("account_id") != account_id:
                continue
            debit = _to_decimal(e.get("debit"))
            credit = _to_decimal(e.get("credit"))
            if account_type in {"asset", "expense"}:
                net += debit - credit
            else:
                net += credit - debit
    return net


def build_reconcile_preview(account: dict, journals: list):
    net_change = _account_net_change(account, journals)

    income_total = Decimal("0")
    expense_total = Decimal("0")
    for j in journals:
        for e in j.get("entries", []):
            debit = _to_decimal(e.get("debit"))
            credit = _to_decimal(e.get("credit"))
            if e.get("account_id") == "income" and credit > 0:
                income_total += credit
            if e.get("account_id") == "expense" and debit > 0:
                expense_total += debit

    expected_change = income_total - expense_total
    diff = expected_change - net_change
    adjustment_amount = abs(diff)

    target_account_id = account.get("id")
    target_currency = (account.get("currency") or "CNY").upper()
    desc = (
        f"AI平账调整-{account.get('name')}-"
        f"{journals[-1].get('date') if journals else ''}"
    )

    if adjustment_amount == 0:
        entries = []
    else:
        if account.get("type") in {"asset", "expense"}:
            if diff > 0:
                # target account should increase
                entries = [
                    {
                        "account_id": target_account_id,
                        "category_id": "",
                        "debit": str(adjustment_amount),
                        "credit": "0.00",
                        "currency": target_currency,
                        "note": "AI平账补差",
                    },
                    {
                        "account_id": "reconcile_adjust",
                        "category_id": "",
                        "debit": "0.00",
                        "credit": str(adjustment_amount),
                        "currency": target_currency,
                        "note": "AI平账对冲",
                    },
                ]
            else:
                entries = [
                    {
                        "account_id": target_account_id,
                        "category_id": "",
                        "debit": "0.00",
                        "credit": str(adjustment_amount),
                        "currency": target_currency,
                        "note": "AI平账冲减",
                    },
                    {
                        "account_id": "reconcile_adjust",
                        "category_id": "",
                        "debit": str(adjustment_amount),
                        "credit": "0.00",
                        "currency": target_currency,
                        "note": "AI平账对冲",
                    },
                ]
        else:
            if diff > 0:
                entries = [
                    {
                        "account_id": target_account_id,
                        "category_id": "",
                        "debit": "0.00",
                        "credit": str(adjustment_amount),
                        "currency": target_currency,
                        "note": "AI平账补差",
                    },
                    {
                        "account_id": "reconcile_adjust",
                        "category_id": "",
                        "debit": str(adjustment_amount),
                        "credit": "0.00",
                        "currency": target_currency,
                        "note": "AI平账对冲",
                    },
                ]
            else:
                entries = [
                    {
                        "account_id": target_account_id,
                        "category_id": "",
                        "debit": str(adjustment_amount),
                        "credit": "0.00",
                        "currency": target_currency,
                        "note": "AI平账冲减",
                    },
                    {
                        "account_id": "reconcile_adjust",
                        "category_id": "",
                        "debit": "0.00",
                        "credit": str(adjustment_amount),
                        "currency": target_currency,
                        "note": "AI平账对冲",
                    },
                ]

    return {
        "account_id": target_account_id,
        "account_name": account.get("name"),
        "income_total": float(income_total),
        "expense_total": float(expense_total),
        "expected_change": float(expected_change),
        "actual_change": float(net_change),
        "diff": float(diff),
        "adjustment_amount": float(adjustment_amount),
        "entries": entries,
        "description": desc,
    }


def commit_reconcile(preview: dict, end_date: str):
    entries = preview.get("entries") or []
    if not entries:
        return {"ok": True, "journal": None, "message": "无需平账"}

    journal, error = create_journal(
        date=end_date,
        description=preview.get("description") or "AI平账调整",
        source="ai_reconcile",
        tags="AI平账",
        entries=entries,
        transfer_lines=[],
    )
    if error:
        return {"ok": False, "error": error}
    return {"ok": True, "journal": journal, "message": "平账已入库"}


from .models import AIAdviceSnapshot, AIConfig


def _runtime_ai_config():
    config = {
        "provider": "google",
        "api_base_url": "",
        "api_key": settings.GOOGLE_API_KEY,
        "model_name": settings.GEMINI_MODEL,
        "system_prompt": "你是专业个人财务顾问。请给出消费建议。",
    }
    try:
        row = AIConfig.objects.order_by("id").first()
    except (OperationalError, ProgrammingError):
        row = None

    if row:
        config["provider"] = row.provider or config["provider"]
        config["api_base_url"] = row.api_base_url or config["api_base_url"]
        config["api_key"] = row.api_key or config["api_key"]
        config["model_name"] = row.model_name or config["model_name"]
        config["system_prompt"] = row.system_prompt or config["system_prompt"]
    return config


def _build_prompt(runtime, summary):
    categories_text = (
        ", ".join(
            [
                f"{x['name']} ¥{x['amount']:.2f}({x['pct']}%)"
                for x in summary.get("categories", [])[:8]
            ]
        )
        or "暂无分类数据"
    )
    return (
        f"{runtime.get('system_prompt')}\n\n"
        "根据以下本月财务数据，用中文给出消费建议。\n"
        "严格返回合法 JSON（不要有多余文字），包含以下字段：\n"
        "  insight: 一句话总结（≤60字）\n"
        "  reason:  原因分析（≤100字）\n"
        "  actions: 3条具体可操作建议（字符串数组，每条≤40字）\n"
        "  goal:    本月/下月一个量化目标（≤40字）\n"
        "  warnings: 消费占比过高的类别名称列表（字符串数组，可为空[]）\n\n"
        f"月份: {summary.get('month')}\n"
        f"收入: ¥{summary.get('income', 0):.2f}\n"
        f"支出: ¥{summary.get('expense', 0):.2f}\n"
        f"净额: ¥{summary.get('net', 0):.2f}\n"
        f"储蓄率: {summary.get('savings_rate', 0)}%\n"
        f"日均支出: ¥{summary.get('avg_daily_expense', 0):.2f}\n"
        f"消费分类: {categories_text}\n"
    )


def _normalize_openai_base_url(base_url: str) -> str:
    url = (base_url or "").strip().rstrip("/")
    if not url:
        return ""
    if url.endswith("/v1"):
        return url
    return f"{url}/v1"


def _openai_compatible_generate(runtime, prompt):
    base_url = _normalize_openai_base_url(runtime.get("api_base_url", ""))
    if not base_url:
        return ""

    headers = {"Content-Type": "application/json"}
    if runtime.get("api_key"):
        headers["Authorization"] = f"Bearer {runtime.get('api_key')}"

    payload = {
        "model": runtime.get("model_name") or "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }

    response = httpx.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


def _google_generate(runtime, prompt):
    client_kwargs = {"api_key": runtime.get("api_key")}
    if runtime.get("api_base_url"):
        client_kwargs["http_options"] = {"base_url": runtime.get("api_base_url")}
    try:
        client = genai.Client(**client_kwargs)
    except Exception:
        client = genai.Client(api_key=runtime.get("api_key"))

    response = client.models.generate_content(
        model=runtime.get("model_name"), contents=prompt
    )
    return (response.text or "").strip()


def _rule_based_advice(summary):
    top = summary.get("top_categories", [])
    expense = summary.get("expense", 0)
    categories_detail = summary.get("categories", [])

    top_text = (
        "、".join([f"{x['name']}({x['amount']:.2f})" for x in top]) if top else "暂无"
    )

    # Identify categories that are >30% of total spend → warnings
    warnings = [x["name"] for x in categories_detail if x.get("pct", 0) > 30]

    actions = [
        "把非必要消费设置每周上限，并在清单中先标记优先级。",
        "将大额支出拆分到月预算中，提前做资金预留。",
        "每周回顾一次 TOP 类别，连续两周超标就降频。",
    ]

    return {
        "month": summary.get("month"),
        "mode": "rules",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "insight": f"本月支出 {expense:.2f}，消费主要集中在：{top_text}。",
        "reason": "当前支出集中度较高，说明少数类别对总支出影响显著。",
        "actions": actions,
        "goal": "下月将 TOP1 分类支出降低 10%-15%。",
        "warnings": warnings,
    }


def _parse_llm_json(text: str) -> dict:
    """Extract first JSON object from LLM response text."""
    # Strip markdown fences
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find a JSON block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return {}


def _llm_advice(summary, fallback):
    runtime = _runtime_ai_config()
    if not runtime.get("api_key"):
        return fallback

    provider = runtime.get("provider", "google")
    prompt = _build_prompt(runtime, summary)

    try:
        if provider == "google":
            text = _google_generate(runtime, prompt)
        else:
            text = _openai_compatible_generate(runtime, prompt)
    except Exception:
        return fallback

    if not text:
        return fallback

    parsed = _parse_llm_json(text)
    if not parsed.get("insight"):
        # If parsing failed, use fallback values but mark as gemini attempt
        return {
            **fallback,
            "mode": "gemini",
            "raw_text": text,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }

    return {
        "month": summary.get("month"),
        "mode": "gemini",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "insight": parsed.get("insight", fallback["insight"]),
        "reason": parsed.get("reason", fallback["reason"]),
        "actions": parsed.get("actions", fallback["actions"]),
        "goal": parsed.get("goal", fallback["goal"]),
        "warnings": parsed.get("warnings", fallback.get("warnings", [])),
        "raw_text": text,
    }


def generate_monthly_advice(month: str, force_refresh: bool = False):
    if not force_refresh:
        row = AIAdviceSnapshot.objects.filter(month=month).first()
        if row and row.payload:
            return row.payload

    summary = monthly_summary(month)
    fallback = _rule_based_advice(summary)
    advice = _llm_advice(summary, fallback)
    AIAdviceSnapshot.objects.update_or_create(month=month, defaults={"payload": advice})
    return advice


def test_ai_connection():
    runtime = _runtime_ai_config()
    provider = runtime.get("provider", "google")
    if not runtime.get("api_key"):
        return {
            "ok": False,
            "message": "未配置 API Key，无法测试连接。",
            "provider": provider,
            "model": runtime.get("model_name", ""),
        }

    test_summary = {
        "month": "2099-01",
        "income": 10000,
        "expense": 4500,
        "net": 5500,
        "savings_rate": 55,
        "avg_daily_expense": 150,
        "categories": [
            {"name": "餐饮", "amount": 1200, "pct": 26.7},
            {"name": "交通", "amount": 600, "pct": 13.3},
        ],
    }
    prompt = _build_prompt(runtime, test_summary)
    try:
        if provider == "google":
            text = _google_generate(runtime, prompt)
        else:
            text = _openai_compatible_generate(runtime, prompt)
    except Exception as exc:
        return {
            "ok": False,
            "message": f"连接失败: {exc}",
            "provider": provider,
            "model": runtime.get("model_name", ""),
        }

    if not text:
        return {
            "ok": False,
            "message": "连接成功，但返回为空。",
            "provider": provider,
            "model": runtime.get("model_name", ""),
        }
    return {
        "ok": True,
        "message": "连接成功，已收到模型响应。",
        "provider": provider,
        "model": runtime.get("model_name", ""),
    }
