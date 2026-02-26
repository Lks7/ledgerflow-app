from datetime import datetime, date
from django.http import JsonResponse
from django.shortcuts import render

from ai_advisor.services import generate_monthly_advice

from .services import (
    current_month,
    current_year,
    monthly_summary,
    summary_for_period,
    yearly_summary,
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

    # AI advice still uses month summary as baseline.
    month = current_month()
    advice = generate_monthly_advice(month)
    return render(
        request,
        "analytics/dashboard.html",
        {"summary": summary, "advice": advice, "period": period},
    )


def reports_page(request):
    month = request.GET.get("month") or current_month()
    year = month[:4]
    force = request.GET.get("refresh") == "1"

    monthly = monthly_summary(month)
    yearly = yearly_summary(year)
    advice = generate_monthly_advice(month, force_refresh=force)

    return render(
        request,
        "analytics/reports.html",
        {
            "month": month,
            "year": year,
            "monthly": monthly,
            "yearly": yearly,
            "advice": advice,
            "prev_month": _adjacent_month(month, -1),
            "next_month": _adjacent_month(month, +1),
            "current_month": current_month(),
        },
    )


def monthly_summary_api(request):
    month = request.GET.get("month") or current_month()
    return JsonResponse(monthly_summary(month))


def yearly_summary_api(request):
    year = request.GET.get("year") or current_year()
    return JsonResponse(yearly_summary(year))
