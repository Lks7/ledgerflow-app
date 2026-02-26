import csv
from datetime import datetime

from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import redirect, render

from .services import (
    account_used_count,
    build_category_tree,
    create_category,
    create_account,
    create_journal,
    delete_account,
    delete_journal,
    delete_tag,
    get_active_accounts,
    get_accounts,
    get_categories,
    get_journal,
    list_all_tags,
    list_categories_with_usage,
    list_journal_logs,
    list_journals,
    rename_tag,
    set_account_balance,
    set_account_status,
    recalculate_account_balances,
    update_category,
    update_account,
    update_journal,
    update_journal_metadata,
    delete_category,
    PROTECTED_ACCOUNT_IDS,
)


def journal_list(request):
    def _to_amount(value):
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    month = request.GET.get("month") or datetime.now().strftime("%Y-%m")
    tag = request.GET.get("tag", "").strip()
    raw_journals = list_journals(month)
    tags = sorted({t for j in raw_journals for t in (j.get("tags") or [])})
    account_map = {x.get("id"): x.get("name") for x in get_accounts()}
    categories = get_categories()
    category_map = {x.get("id"): x.get("name") for x in categories}
    journals = []
    for journal in list_journals(month, tag=tag):
        entries = []
        primary_category_id = ""
        for entry in journal.get("entries", []):
            row = dict(entry)
            row["account_name"] = account_map.get(
                entry.get("account_id"), entry.get("account_id")
            )
            row["debit_amount"] = _to_amount(entry.get("debit"))
            row["credit_amount"] = _to_amount(entry.get("credit"))
            if not primary_category_id and entry.get("category_id"):
                primary_category_id = entry.get("category_id")
            entries.append(row)

        transfers = []
        for transfer in journal.get("transfers", []):
            item = dict(transfer)
            item["from_name"] = account_map.get(
                transfer.get("from_account_id"), transfer.get("from_account_id")
            )
            item["to_name"] = account_map.get(
                transfer.get("to_account_id"), transfer.get("to_account_id")
            )
            item["display_currency"] = (transfer.get("currency") or "").strip() or "CNY"
            transfers.append(item)

        item = dict(journal)
        item["entries"] = entries
        item["transfers"] = transfers
        item["primary_category_id"] = primary_category_id
        item["primary_category_name"] = category_map.get(primary_category_id, "")
        item["tags_str"] = ",".join(journal.get("tags") or [])
        journals.append(item)

    context = {
        "month": month,
        "tag": tag,
        "tags": tags,
        "categories": categories,
        "journals": journals,
    }
    return render(request, "ledger/journal_list.html", context)


def journal_new(request):
    prefill_desc = request.GET.get("desc", "")
    prefill_tags = request.GET.get("tags", "")
    prefill_source = request.GET.get("source", "manual")
    prefill_amount = request.GET.get("amount", "0")
    try:
        prefill_amount_float = float(prefill_amount)
    except (ValueError, TypeError):
        prefill_amount_float = 0.0

    import json as _json

    prefill_json = _json.dumps({"amount": prefill_amount_float})

    context = {
        "today": datetime.now().strftime("%Y-%m-%d"),
        "accounts": get_active_accounts(),
        "categories": get_categories(),
        "default_currency": "CNY",
        "prefill_desc": prefill_desc,
        "prefill_tags": prefill_tags,
        "prefill_source": prefill_source,
        "prefill_amount": prefill_amount_float,
        "prefill_json": prefill_json,
    }
    return render(request, "ledger/journal_new.html", context)


def _entry_from_request(request, index: int):
    return {
        "account_id": request.POST.get(f"account_id_{index}", ""),
        "category_id": request.POST.get(f"category_id_{index}", ""),
        "debit": request.POST.get(f"debit_{index}", "0"),
        "credit": request.POST.get(f"credit_{index}", "0"),
        "currency": request.POST.get(f"currency_{index}", "CNY"),
        "note": request.POST.get(f"note_{index}", ""),
    }


def _has_entry_content(entry: dict) -> bool:
    def _to_num(value):
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    return any(
        [
            (entry.get("account_id") or "").strip(),
            (entry.get("category_id") or "").strip(),
            _to_num(entry.get("debit")) > 0,
            _to_num(entry.get("credit")) > 0,
            (entry.get("note") or "").strip(),
        ]
    )


def _transfer_from_request(request, index: int):
    return {
        "from_account_id": request.POST.get(f"from_account_id_{index}", ""),
        "to_account_id": request.POST.get(f"to_account_id_{index}", ""),
        "amount": request.POST.get(f"transfer_amount_{index}", "0"),
        "currency": request.POST.get(f"transfer_currency_{index}", "CNY"),
        "note": request.POST.get(f"transfer_note_{index}", ""),
    }


def journal_create(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")

    date = request.POST.get("date", "")
    description = request.POST.get("description", "")
    source = request.POST.get("source", "manual")
    tags = request.POST.get("tags", "")

    amount = request.POST.get("amount", "0")
    currency = request.POST.get("currency", "CNY")
    note = request.POST.get("note", "")
    from_acc = request.POST.get("from_account_id", "")
    to_acc = request.POST.get("to_account_id", "")
    cat_id = request.POST.get("category_id", "")

    # We will pass this to `create_journal` as a simplified transfer list,
    # but since `.services` handles categories on entries, we'll format it as an entry pair to support categories

    entries = []
    if from_acc and to_acc and float(amount or 0) > 0:
        entries.append(
            {
                "account_id": to_acc,
                "category_id": cat_id,
                "debit": amount,
                "credit": "0",
                "currency": currency,
                "note": note,
            }
        )
        entries.append(
            {
                "account_id": from_acc,
                "category_id": cat_id,
                "debit": "0",
                "credit": amount,
                "currency": currency,
                "note": note,
            }
        )

    _journal, error = create_journal(
        date, description, source, tags, entries, transfer_lines=[]
    )
    if error:
        context = {
            "today": date,
            "accounts": get_active_accounts(),
            "categories": get_categories(),
            "default_currency": "CNY",
            "error": error,
        }
        messages.error(request, f"记账失败：{error}")
        return render(request, "ledger/journal_new.html", context, status=400)

    messages.success(request, "记账成功")
    return redirect("journal_list")


def journal_delete(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")
    month = request.POST.get("month", "")
    journal_id = request.POST.get("journal_id", "")
    delete_journal(month, journal_id)
    messages.success(request, "记账记录已删除")
    return redirect(f"/journals/?month={month}")


def journal_update_metadata(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")

    month = request.POST.get("month", "")
    journal_id = request.POST.get("journal_id", "")
    tags = request.POST.get("tags", "")
    category_id = request.POST.get("category_id", "")
    _journal, error = update_journal_metadata(journal_id, tags, category_id)
    if error:
        messages.error(request, f"更新失败：{error}")
        return HttpResponseBadRequest(error)
    messages.success(request, "记账信息已更新")
    return redirect(f"/journals/?month={month}")


def _accounts_with_usage():
    accounts = get_accounts()
    recalculate_account_balances(accounts)
    for account in accounts:
        account["usage_count"] = account_used_count(account.get("id"))
        t = account.get("type", "asset")
        account["type_is_asset"] = t == "asset"
        account["type_is_liability"] = t == "liability"
        account["type_is_income"] = t == "income"
        account["type_is_expense"] = t == "expense"
    return accounts


_ACCOUNT_GROUP_META = [
    {
        "type": "asset",
        "label": "资产账户",
        "icon": "💰",
        "desc": "你拥有的钱：现金、银行卡、저蓄等",
    },
    {
        "type": "liability",
        "label": "负债账户",
        "icon": "💳",
        "desc": "你欠别人的钱：信用卡、花呗、贷款等",
    },
    {
        "type": "income",
        "label": "收入账户",
        "icon": "📈",
        "desc": "钱的来源：工资、奖金、副业收入等",
    },
    {
        "type": "expense",
        "label": "支出账户",
        "icon": "📉",
        "desc": "钱的去向：餐饮、交通、购物等",
    },
]


def _build_account_groups(accounts):
    from decimal import Decimal

    buckets = {m["type"]: [] for m in _ACCOUNT_GROUP_META}
    for acc in accounts:
        t = acc.get("type", "asset")
        if t in buckets:
            buckets[t].append(acc)

    groups = []
    for meta in _ACCOUNT_GROUP_META:
        accs = buckets[meta["type"]]
        try:
            total = sum(Decimal(str(a.get("balance") or "0")) for a in accs)
        except Exception:
            total = 0
        groups.append(
            {
                **meta,
                "accounts": accs,
                "total": f"{total:.2f}",
            }
        )
    return groups


def account_settings(request):
    accounts = _accounts_with_usage()
    context = {
        "accounts": accounts,
        "account_groups": _build_account_groups(accounts),
        "protected_ids": PROTECTED_ACCOUNT_IDS,
    }
    return render(request, "ledger/account_settings.html", context)


def account_create(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")

    _account, error = create_account(
        name=request.POST.get("name", ""),
        account_type=request.POST.get("type", "asset"),
        currency=request.POST.get("currency", "CNY"),
        opening_balance=request.POST.get("opening_balance", "0"),
        note=request.POST.get("note", ""),
    )
    if error:
        accounts = _accounts_with_usage()
        messages.error(request, f"新增账户失败：{error}")
        return render(
            request,
            "ledger/account_settings.html",
            {
                "accounts": accounts,
                "account_groups": _build_account_groups(accounts),
                "error": error,
            },
            status=400,
        )
    messages.success(request, "账户新增成功")
    return redirect("account_settings")


def account_update_status(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")
    account_id = request.POST.get("account_id", "")
    status = request.POST.get("status", "active")
    ok, error = set_account_status(account_id, status)
    if not ok:
        accounts = _accounts_with_usage()
        messages.error(request, f"状态更新失败：{error}")
        return render(
            request,
            "ledger/account_settings.html",
            {
                "accounts": accounts,
                "account_groups": _build_account_groups(accounts),
                "error": error,
            },
            status=400,
        )
    messages.success(request, "账户状态已更新")
    return redirect("account_settings")


def account_delete(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")
    account_id = request.POST.get("account_id", "")
    ok, error = delete_account(account_id)
    if not ok:
        accounts = _accounts_with_usage()
        messages.error(request, f"删除账户失败：{error}")
        return render(
            request,
            "ledger/account_settings.html",
            {
                "accounts": accounts,
                "account_groups": _build_account_groups(accounts),
                "error": error,
            },
            status=400,
        )
    messages.success(request, "账户已删除")
    return redirect("account_settings")


def account_set_balance(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")
    account_id = request.POST.get("account_id", "")
    opening_balance = request.POST.get("opening_balance", "0")
    ok, error = set_account_balance(account_id, opening_balance)
    if not ok:
        accounts = _accounts_with_usage()
        messages.error(request, f"设置余额失败：{error}")
        return render(
            request,
            "ledger/account_settings.html",
            {
                "accounts": accounts,
                "account_groups": _build_account_groups(accounts),
                "error": error,
            },
            status=400,
        )
    messages.success(request, "期初余额已更新")
    return redirect("account_settings")


def account_update(request):
    """Update account name and/or type."""
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")
    account_id = request.POST.get("account_id", "")
    name = request.POST.get("name", "").strip()
    account_type = request.POST.get("type", "asset")
    currency = request.POST.get("currency", "CNY")
    note = request.POST.get("note", "")
    ok, error = update_account(account_id, name, account_type, currency, note)
    if not ok:
        accounts = _accounts_with_usage()
        messages.error(request, f"更新账户失败：{error}")
        return render(
            request,
            "ledger/account_settings.html",
            {
                "accounts": accounts,
                "account_groups": _build_account_groups(accounts),
                "error": error,
            },
            status=400,
        )
    messages.success(request, "账户信息已更新")
    return redirect("account_settings")


def journal_logs(request):
    logs = list_journal_logs(limit=300)
    return render(request, "ledger/journal_logs.html", {"logs": logs})


# ── Journal Edit ────────────────────────────────────────────────────────────


def journal_edit(request, month, journal_id):
    journal = get_journal(month, journal_id)
    if not journal:
        return HttpResponseNotFound("凭证不存在")
    account_map = {x.get("id"): x.get("name") for x in get_accounts()}
    # Enrich entries with account names for template display
    entries = []
    for e in journal.get("entries", []):
        row = dict(e)
        row["account_name"] = account_map.get(
            e.get("account_id"), e.get("account_id", "")
        )
        entries.append(row)
    context = {
        "journal": {**journal, "entries": entries},
        "month": month,
        "accounts": get_active_accounts(),
        "categories": get_categories(),
        "default_currency": "CNY",
        "tags_str": ",".join(journal.get("tags") or []),
    }
    return render(request, "ledger/journal_edit.html", context)


def journal_update(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")

    month = request.POST.get("month", "")
    journal_id = request.POST.get("journal_id", "")
    date = request.POST.get("date", "")
    description = request.POST.get("description", "")
    source = request.POST.get("source", "manual")
    tags = request.POST.get("tags", "")

    amount = request.POST.get("amount", "0")
    currency = request.POST.get("currency", "CNY")
    note = request.POST.get("note", "")
    from_acc = request.POST.get("from_account_id", "")
    to_acc = request.POST.get("to_account_id", "")
    cat_id = request.POST.get("category_id", "")

    entries = []
    if from_acc and to_acc and float(amount or 0) > 0:
        entries.append(
            {
                "account_id": to_acc,
                "category_id": cat_id,
                "debit": amount,
                "credit": "0",
                "currency": currency,
                "note": note,
            }
        )
        entries.append(
            {
                "account_id": from_acc,
                "category_id": cat_id,
                "debit": "0",
                "credit": amount,
                "currency": currency,
                "note": note,
            }
        )

    _journal, error = update_journal(
        month, journal_id, date, description, source, tags, entries, transfer_lines=[]
    )
    if error:
        journal_raw = get_journal(month, journal_id) or {}
        context = {
            "journal": journal_raw,
            "month": month,
            "accounts": get_active_accounts(),
            "categories": get_categories(),
            "default_currency": "CNY",
            "tags_str": tags,
            "error": error,
        }
        messages.error(request, f"更新记账失败：{error}")
        return render(request, "ledger/journal_edit.html", context, status=400)

    messages.success(request, "记账记录已更新")
    return redirect(f"/journals/?month={month}")


# ── CSV Export ──────────────────────────────────────────────────────────────


def journal_export_csv(request):
    month = request.GET.get("month") or datetime.now().strftime("%Y-%m")
    journals = list_journals(month)
    account_map = {x.get("id"): x.get("name") for x in get_accounts()}

    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = f'attachment; filename="journals_{month}.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "日期",
            "说明",
            "标签",
            "资金流向",
            "金额",
            "账户",
            "借方",
            "贷方",
            "币种",
            "备注",
        ]
    )
    for j in journals:
        tags_str = ",".join(j.get("tags") or [])
        # Write one row per transfer (flow summary)
        transfers = j.get("transfers") or []
        entries = j.get("entries") or []
        if transfers:
            for t in transfers:
                flow = f"{account_map.get(t.get('from_account_id'), t.get('from_account_id', ''))} → {account_map.get(t.get('to_account_id'), t.get('to_account_id', ''))}"
                writer.writerow(
                    [
                        j.get("date"),
                        j.get("description"),
                        tags_str,
                        flow,
                        t.get("amount"),
                        "",
                        "",
                        "",
                        t.get("currency", "CNY"),
                        t.get("note", ""),
                    ]
                )
        for e in entries:
            writer.writerow(
                [
                    j.get("date"),
                    j.get("description"),
                    tags_str,
                    "",
                    "",
                    account_map.get(e.get("account_id"), e.get("account_id", "")),
                    e.get("debit"),
                    e.get("credit"),
                    e.get("currency", "CNY"),
                    e.get("note", ""),
                ]
            )
    return response


def account_export_csv(request):
    accounts = get_accounts()
    recalculate_account_balances(accounts)

    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="accounts.csv"'

    writer = csv.writer(response)
    writer.writerow(["账户名", "类型", "币种", "期初金额", "当前余额", "状态"])
    type_map = {
        "asset": "资产",
        "liability": "负债",
        "expense": "费用",
        "income": "收入",
    }
    status_map = {"active": "启用", "inactive": "停用"}
    for a in accounts:
        writer.writerow(
            [
                a.get("name"),
                type_map.get(a.get("type", ""), a.get("type", "")),
                a.get("currency", "CNY"),
                a.get("opening_balance", "0.00"),
                a.get("balance", "0.00"),
                status_map.get(a.get("status", ""), a.get("status", "")),
            ]
        )
    return response


# ── Tag Management ───────────────────────────────────────────────────────────


def tag_settings(request):
    tags = list_all_tags()
    return render(request, "ledger/tag_settings.html", {"tags": tags})


def tag_rename(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")
    old = (request.POST.get("old_tag") or "").strip()
    new = (request.POST.get("new_tag") or "").strip()
    if not old or not new:
        tags = list_all_tags()
        messages.error(request, "旧名/新名不能为空")
        return render(
            request,
            "ledger/tag_settings.html",
            {"tags": tags, "error": "旧名/新名不能为空"},
            status=400,
        )
    if old == new:
        return redirect("tag_settings")
    rename_tag(old, new)
    messages.success(request, f"标签「{old}」已重命名为「{new}」")
    return redirect("tag_settings")


def tag_delete(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")
    tag = (request.POST.get("tag") or "").strip()
    if tag:
        delete_tag(tag)
        messages.success(request, f"标签「{tag}」已删除")
    return redirect("tag_settings")


def category_settings(request):
    flat = list_categories_with_usage()
    tree = build_category_tree(flat)
    # Collect unique groups for display
    groups = sorted({c["group"] for c in flat if c.get("group")})
    # All categories as flat list for parent dropdown
    return render(
        request,
        "ledger/category_settings.html",
        {
            "category_tree": tree,
            "categories_flat": flat,
            "groups": groups,
        },
    )


def category_create(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")

    _cat, error = create_category(
        name=request.POST.get("name", ""),
        group=request.POST.get("group", ""),
        budget_monthly=request.POST.get("budget_monthly", "0"),
        category_id=request.POST.get("id", ""),
        parent_id=request.POST.get("parent_id", ""),
        icon=request.POST.get("icon", ""),
    )
    if error:
        messages.error(request, f"新增分类失败：{error}")
    else:
        messages.success(request, "分类新增成功")
    return redirect("category_settings")


def category_update(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")

    category_id = request.POST.get("category_id", "")
    ok, error = update_category(
        category_id=category_id,
        name=request.POST.get("name", ""),
        group=request.POST.get("group", ""),
        budget_monthly=request.POST.get("budget_monthly", "0"),
        icon=request.POST.get("icon", ""),
        parent_id=request.POST.get("parent_id", ""),
    )
    if not ok:
        messages.error(request, f"更新分类失败：{error}")
    else:
        messages.success(request, "分类已更新")
    return redirect("category_settings")


def category_delete(request):
    if request.method != "POST":
        return HttpResponseBadRequest("只支持 POST")

    category_id = (request.POST.get("category_id") or "").strip()
    ok, error = delete_category(category_id)
    if not ok:
        messages.error(request, f"删除分类失败：{error}")
    else:
        messages.success(request, "分类已删除")
    return redirect("category_settings")
