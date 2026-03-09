from datetime import datetime, date
from django.http import JsonResponse
from django.shortcuts import redirect, render

from ai_advisor.services import generate_monthly_advice
from ledger.services import get_accounts

from .services import (
    current_month,
    current_year,
    monthly_summary,
    summary_for_period,
    yearly_summary,
    yearly_daily_expenses,
)


def _adjacent_month(month: str, delta: int) -> str:
    """Return month string offset by `delta` months."""
    try:
        y, m = map(int, month.split("-"))
        m += delta
        while m > 12:
            m -= 12
            y += 1
        while m < 1:
            m += 12
            y -= 1
        return f"{y}-{str(m).zfill(2)}"
    except Exception:
        return month


def dashboard(request):
    period = request.GET.get("period", "month")
    if period not in {"day", "week", "month", "year"}:
        period = "month"

    summary = summary_for_period(period)

    today = date.today()
    default_end_date = today.isoformat()
    default_start_date = (today.fromordinal(today.toordinal() - 30)).isoformat()

    # Needs json dumps for the frontend echarts
    import json

    categories_raw_json = json.dumps(summary.get("categories_raw", []))

    yearly_expenses_json = json.dumps(yearly_daily_expenses(current_year()))

    return render(
        request,
        "analytics/dashboard.html",
        {
            "summary": summary,
            "period": period,
            "categories_raw_json": categories_raw_json,
            "yearly_expenses_json": yearly_expenses_json,
            "accounts": get_accounts(),
            "default_start_date": default_start_date,
            "default_end_date": default_end_date,
        },
    )


def reports_page(request):
    # Deprecated: reports page removed. Redirect to financial report.
    return redirect("financial_report")


def monthly_summary_api(request):
    month = request.GET.get("month") or current_month()
    return JsonResponse(monthly_summary(month))


def yearly_summary_api(request):
    year = request.GET.get("year") or current_year()
    return JsonResponse(yearly_summary(year))
