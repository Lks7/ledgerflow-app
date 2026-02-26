from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from calendar import monthrange

from django.db.models import Sum
from ledger.models import Account, Category, Journal, JournalEntry


def _months_in_year(year: str):
    return [f"{year}-{str(i).zfill(2)}" for i in range(1, 13)]


def _summary_for_dates(
    start_date: date, end_date: date, period: str, period_label: str
):
    journals = Journal.objects.filter(
        date__range=[start_date, end_date]
    ).prefetch_related("entries")

    income = Decimal("0.00")
    expense = Decimal("0.00")
    category_totals = defaultdict(Decimal)
    tag_counts: dict[str, int] = {}

    accounts = {a.id: a for a in Account.objects.all()}
    category_names = _load_categories()

    for journal in journals:
        for tag in journal.get_tags():
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        for entry in journal.entries.all():
            debit = entry.debit
            credit = entry.credit
            category_id = entry.category_id or "uncategorized"
            account = accounts.get(entry.account_id)
            if not account:
                continue
            account_type = account.type

            if debit > 0 and account_type == "expense":
                expense += debit
                category_totals[category_id] += debit
            if credit > 0 and account_type == "income":
                income += credit

    net = income - expense
    savings_rate = round(float(net / income * 100), 1) if income > 0 else 0.0

    days_count = max((end_date - start_date).days + 1, 1)
    avg_daily_expense = round(float(expense) / days_count, 2)

    sorted_categories = sorted(
        category_totals.items(), key=lambda x: x[1], reverse=True
    )

    top_tag = max(tag_counts, key=tag_counts.get) if tag_counts else ""

    categories_detail = [
        {
            "category_id": k,
            "name": category_names.get(k, k) if k != "uncategorized" else "未分类",
            "amount": float(v),
            "pct": round(float(v / expense * 100), 1) if expense > 0 else 0.0,
        }
        for k, v in sorted_categories
    ]

    return {
        "period": period,
        "period_label": period_label,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "income": float(income),
        "expense": float(expense),
        "net": float(net),
        "savings_rate": savings_rate,
        "avg_daily_expense": avg_daily_expense,
        "journal_count": len(journals),
        "top_tag": top_tag,
        "categories": categories_detail,
        "top_categories": categories_detail[:3],
        "categories_raw": [
            {"category_id": k, "amount": float(v)} for k, v in sorted_categories
        ],
    }


def _load_categories() -> dict:
    """Return {id: name} map for all categories."""
    return {c.id: c.name for c in Category.objects.all()}


def monthly_summary(month: str):
    try:
        y, m = map(int, month.split("-"))
        start_date = date(y, m, 1)
        end_date = date(y, m, monthrange(y, m)[1])
    except Exception:
        now = datetime.now().date()
        start_date = date(now.year, now.month, 1)
        end_date = date(now.year, now.month, monthrange(now.year, now.month)[1])

    summary = _summary_for_dates(start_date, end_date, "month", "本月")
    summary["month"] = month
    return summary


def summary_for_period(period: str):
    today = datetime.now().date()

    if period == "day":
        return _summary_for_dates(today, today, "day", "今日")

    if period == "week":
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        return _summary_for_dates(start_date, end_date, "week", "本周")

    if period == "year":
        start_date = date(today.year, 1, 1)
        end_date = date(today.year, 12, 31)
        return _summary_for_dates(start_date, end_date, "year", "本年")

    start_date = date(today.year, today.month, 1)
    end_date = date(today.year, today.month, monthrange(today.year, today.month)[1])
    return _summary_for_dates(start_date, end_date, "month", "本月")


def yearly_summary(year: str):
    totals = []
    total_income = Decimal("0.00")
    total_expense = Decimal("0.00")

    for month in _months_in_year(year):
        item = monthly_summary(month)
        totals.append(
            {
                "month": month,
                "income": item["income"],
                "expense": item["expense"],
                "net": item["net"],
            }
        )
        total_income += Decimal(str(item["income"]))
        total_expense += Decimal(str(item["expense"]))

    return {
        "year": year,
        "income": float(total_income),
        "expense": float(total_expense),
        "net": float(total_income - total_expense),
        "months": totals,
    }


def current_month() -> str:
    return datetime.now().strftime("%Y-%m")


def current_year() -> str:
    return datetime.now().strftime("%Y")
