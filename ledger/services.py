import uuid
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction

from .models import (
    Account,
    Category,
    Journal,
    JournalEntry,
    JournalLog,
    JournalTransfer,
)

PROTECTED_ACCOUNT_IDS = {"expense", "income"}


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def _account_to_dict(a: Account) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "type": a.type,
        "currency": a.currency,
        "status": a.status,
        "opening_balance": str(a.opening_balance),
        "balance": str(a.balance),
        "note": a.note,
    }


COMMON_ACCOUNTS = [
    {
        "id": "general",
        "name": "通用账户",
        "type": "asset",
        "status": "active",
        "currency": "CNY",
        "opening_balance": "0.00",
        "balance": "0.00",
    },
    {
        "id": "cash",
        "name": "现金",
        "type": "asset",
        "status": "active",
        "currency": "CNY",
        "opening_balance": "0.00",
        "balance": "0.00",
    },
    {
        "id": "wechat",
        "name": "微信",
        "type": "asset",
        "status": "active",
        "currency": "CNY",
        "opening_balance": "0.00",
        "balance": "0.00",
    },
    {
        "id": "alipay",
        "name": "支付宝",
        "type": "asset",
        "status": "active",
        "currency": "CNY",
        "opening_balance": "0.00",
        "balance": "0.00",
    },
    {
        "id": "boc",
        "name": "中国银行",
        "type": "asset",
        "status": "active",
        "currency": "CNY",
        "opening_balance": "0.00",
        "balance": "0.00",
    },
    {
        "id": "cmb",
        "name": "招商银行",
        "type": "asset",
        "status": "active",
        "currency": "CNY",
        "opening_balance": "0.00",
        "balance": "0.00",
    },
    {
        "id": "expense",
        "name": "费用汇总",
        "type": "expense",
        "status": "active",
        "currency": "CNY",
        "opening_balance": "0.00",
        "balance": "0.00",
    },
    {
        "id": "income",
        "name": "收入汇总",
        "type": "income",
        "status": "active",
        "currency": "CNY",
        "opening_balance": "0.00",
        "balance": "0.00",
    },
]


def _ensure_common_accounts():
    if not Account.objects.filter(id="general").exists():
        with transaction.atomic():
            for acc in COMMON_ACCOUNTS:
                Account.objects.get_or_create(
                    id=acc["id"],
                    defaults=dict(
                        name=acc["name"],
                        type=acc["type"],
                        status=acc["status"],
                        currency=acc["currency"],
                        opening_balance=Decimal(acc["opening_balance"]),
                        balance=Decimal(acc["balance"]),
                    ),
                )


def get_accounts():
    _ensure_common_accounts()
    return [_account_to_dict(a) for a in Account.objects.all()]


def get_categories():
    return [
        {
            "id": c.id,
            "name": c.name,
            "group": c.group,
            "budget_monthly": str(c.budget_monthly),
        }
        for c in Category.objects.all()
    ]


def _slugify_category_id(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9_-]", "", value)
    return value


def category_used_count(category_id: str) -> int:
    return JournalEntry.objects.filter(category_id=category_id).count()


def list_categories_with_usage() -> list:
    items = []
    for c in Category.objects.all():
        items.append(
            {
                "id": c.id,
                "name": c.name,
                "icon": c.icon,
                "group": c.group,
                "parent_id": c.parent_id or "",
                "budget_monthly": str(c.budget_monthly),
                "usage_count": category_used_count(c.id),
            }
        )
    return items


def build_category_tree(flat_list: list) -> list:
    """Build a tree from flat category list. Each root gets a 'children' list."""
    by_id = {c["id"]: {**c, "children": []} for c in flat_list}
    roots = []
    for c in flat_list:
        pid = c.get("parent_id") or ""
        if pid and pid in by_id:
            by_id[pid]["children"].append(by_id[c["id"]])
        else:
            roots.append(by_id[c["id"]])
    return roots


def create_category(
    name: str,
    group: str = "",
    budget_monthly: str = "0",
    category_id: str = "",
    parent_id: str = "",
    icon: str = "",
):
    category_name = (name or "").strip()
    if not category_name:
        return None, "分类名称不能为空。"

    cid = _slugify_category_id(category_id) or _slugify_category_id(category_name)
    if not cid:
        cid = str(uuid.uuid4())

    if Category.objects.filter(id=cid).exists():
        return None, "分类 ID 已存在，请换一个。"

    parent = None
    if parent_id:
        try:
            parent = Category.objects.get(id=parent_id)
        except Category.DoesNotExist:
            return None, "父分类不存在。"

    category = Category.objects.create(
        id=cid,
        name=category_name,
        icon=(icon or "").strip(),
        group=(group or "").strip(),
        parent=parent,
        budget_monthly=_to_decimal(budget_monthly),
    )
    return {
        "id": category.id,
        "name": category.name,
        "icon": category.icon,
        "group": category.group,
        "parent_id": category.parent_id or "",
        "budget_monthly": str(category.budget_monthly),
    }, ""


def update_category(
    category_id: str,
    name: str,
    group: str,
    budget_monthly: str,
    icon: str = "",
    parent_id: str = "",
):
    if not name or not name.strip():
        return False, "分类名称不能为空。"
    try:
        cat = Category.objects.get(id=category_id)
        cat.name = name.strip()
        cat.icon = (icon or "").strip()
        cat.group = (group or "").strip()
        cat.budget_monthly = _to_decimal(budget_monthly)
        # Update parent (prevent self-reference)
        if parent_id and parent_id != category_id:
            try:
                cat.parent = Category.objects.get(id=parent_id)
            except Category.DoesNotExist:
                pass
        elif not parent_id:
            cat.parent = None
        cat.save()
        return True, ""
    except Category.DoesNotExist:
        return False, "分类不存在。"


def delete_category(category_id: str):
    if category_used_count(category_id) > 0:
        return False, "该分类已有记账记录，暂不允许删除。"
    try:
        cat = Category.objects.get(id=category_id)
        # Re-parent children to this category's parent
        Category.objects.filter(parent_id=category_id).update(parent=cat.parent)
        cat.delete()
        return True, ""
    except Category.DoesNotExist:
        return False, "分类不存在。"


def _journal_to_dict(j: Journal) -> dict:
    return {
        "id": j.id,
        "date": str(j.date),
        "description": j.description,
        "source": j.source,
        "tags": j.get_tags(),
        "entries": [
            {
                "account_id": e.account_id,
                "category_id": e.category_id,
                "debit": str(e.debit),
                "credit": str(e.credit),
                "currency": e.currency,
                "note": e.note,
            }
            for e in j.entries.all()
        ],
        "transfers": [
            {
                "from_account_id": t.from_account_id,
                "to_account_id": t.to_account_id,
                "amount": str(t.amount),
                "currency": t.currency,
                "note": t.note,
            }
            for t in j.transfers.all()
        ],
        "created_at": j.created_at.isoformat(),
        "updated_at": j.updated_at.isoformat(),
    }


def list_journals(month: str, tag: str = ""):
    qs = Journal.objects.filter(date__startswith=month).prefetch_related(
        "entries", "transfers"
    )
    qs = qs.order_by("-date", "-created_at")

    journals = []
    for j in qs:
        tags = j.get_tags()
        if tag and tag not in tags:
            continue
        journals.append(_journal_to_dict(j))
    return journals


def _validate_entries(entries):
    _ensure_common_accounts()
    if len(entries) < 2:
        return "至少需要两条分录。"

    debit_sum = Decimal("0.00")
    credit_sum = Decimal("0.00")
    account_ids = [e.get("account_id") for e in entries if e.get("account_id")]
    accounts_db = dict(
        Account.objects.filter(id__in=account_ids).in_bulk(field_name="id")
    )

    for entry in entries:
        account_id = entry.get("account_id", "")
        account = accounts_db.get(account_id)
        if not account:
            return f"账户不存在: {account_id or '未选择'}。"
        if account.status != "active":
            return f"账户已停用，不能记账: {account.name}。"

        debit = _to_decimal(entry.get("debit", "0"))
        credit = _to_decimal(entry.get("credit", "0"))
        if debit < 0 or credit < 0:
            return "借方或贷方金额不能为负数。"
        debit_sum += debit
        credit_sum += credit

    if debit_sum != credit_sum:
        return f"借贷不平衡：借方 {debit_sum}，贷方 {credit_sum}。"

    if debit_sum == Decimal("0.00"):
        return "金额不能全为 0。"

    return ""


def _normalize_transfers(transfer_lines):
    normalized = []
    generated_entries = []
    for line in transfer_lines or []:
        from_account_id = (line.get("from_account_id") or "").strip()
        to_account_id = (line.get("to_account_id") or "").strip()
        if not from_account_id or not to_account_id:
            continue
        if from_account_id == to_account_id:
            return [], [], "转出账户和转入账户不能相同。"

        amount = _to_decimal(line.get("amount", "0"))
        if amount <= Decimal("0.00"):
            return [], [], "资金流向金额必须大于 0。"

        currency = (line.get("currency") or "CNY").upper()
        note = (line.get("note") or "").strip()
        normalized.append(
            {
                "from_account_id": from_account_id,
                "to_account_id": to_account_id,
                "amount": str(amount),
                "currency": currency,
                "note": note,
            }
        )
        generated_entries.append(
            {
                "account_id": to_account_id,
                "category_id": "",
                "debit": str(amount),
                "credit": "0.00",
                "currency": currency,
                "note": f"流向转入 {note}".strip(),
            }
        )
        generated_entries.append(
            {
                "account_id": from_account_id,
                "category_id": "",
                "debit": "0.00",
                "credit": str(amount),
                "currency": currency,
                "note": f"流向转出 {note}".strip(),
            }
        )
    return normalized, generated_entries, ""


def create_journal(date, description, source, tags, entries, transfer_lines=None):
    normalized_transfers, transfer_entries, transfer_error = _normalize_transfers(
        transfer_lines
    )
    if transfer_error:
        return None, transfer_error

    combined_entries = (entries or []) + transfer_entries
    if not combined_entries:
        return None, "请至少填写一条资金流向或两条分录。"

    error = _validate_entries(combined_entries)
    if error:
        return None, error

    tag_list = [x.strip() for x in tags.split(",") if x.strip()]

    with transaction.atomic():
        journal = Journal.objects.create(
            id=str(uuid.uuid4()),
            date=date,
            description=description,
            source=source,
            tags_raw=",".join(tag_list),
        )
        for e in combined_entries:
            cat_id = e.get("category_id")
            JournalEntry.objects.create(
                journal=journal,
                account_id=e.get("account_id"),
                category_id=cat_id if cat_id else None,
                debit=_to_decimal(e.get("debit", "0")),
                credit=_to_decimal(e.get("credit", "0")),
                currency=(e.get("currency") or "CNY").upper(),
                note=e.get("note", ""),
            )
        for t in normalized_transfers:
            JournalTransfer.objects.create(
                journal=journal,
                from_account_id=t.get("from_account_id"),
                to_account_id=t.get("to_account_id"),
                amount=_to_decimal(t.get("amount", "0")),
                currency=(t.get("currency") or "CNY").upper(),
                note=t.get("note", ""),
            )

        recalculate_account_balances()

    journal_dict = _journal_to_dict(journal)
    _append_journal_log("create", journal_dict)
    return journal_dict, ""


def get_journal(month: str, journal_id: str):
    # month allows backwards compatibility if needed, but we can ignore it since ID is unique
    try:
        j = Journal.objects.prefetch_related("entries", "transfers").get(id=journal_id)
        return _journal_to_dict(j)
    except Journal.DoesNotExist:
        return None


def delete_journal(month: str, journal_id: str) -> bool:
    try:
        with transaction.atomic():
            j = Journal.objects.get(id=journal_id)
            jd = _journal_to_dict(j)
            j.delete()
            recalculate_account_balances()
            _append_journal_log("delete", jd)
        return True
    except Journal.DoesNotExist:
        return False


def update_journal(
    month: str,
    journal_id: str,
    date: str,
    description: str,
    source: str,
    tags: str,
    entries,
    transfer_lines=None,
):
    try:
        journal = Journal.objects.get(id=journal_id)
    except Journal.DoesNotExist:
        return None, "凭证不存在。"

    normalized_transfers, transfer_entries, transfer_error = _normalize_transfers(
        transfer_lines
    )
    if transfer_error:
        return None, transfer_error

    combined_entries = (entries or []) + transfer_entries
    if not combined_entries:
        return None, "请至少填写一条资金流向或两条分录。"

    error = _validate_entries(combined_entries)
    if error:
        return None, error

    tag_list = [x.strip() for x in tags.split(",") if x.strip()]

    with transaction.atomic():
        journal.date = date
        journal.description = description
        journal.source = source
        journal.tags_raw = ",".join(tag_list)
        journal.save()

        journal.entries.all().delete()
        journal.transfers.all().delete()

        for e in combined_entries:
            cat_id = e.get("category_id")
            JournalEntry.objects.create(
                journal=journal,
                account_id=e.get("account_id"),
                category_id=cat_id if cat_id else None,
                debit=_to_decimal(e.get("debit", "0")),
                credit=_to_decimal(e.get("credit", "0")),
                currency=(e.get("currency") or "CNY").upper(),
                note=e.get("note", ""),
            )
        for t in normalized_transfers:
            JournalTransfer.objects.create(
                journal=journal,
                from_account_id=t.get("from_account_id"),
                to_account_id=t.get("to_account_id"),
                amount=_to_decimal(t.get("amount", "0")),
                currency=(t.get("currency") or "CNY").upper(),
                note=t.get("note", ""),
            )

        recalculate_account_balances()

    jd = _journal_to_dict(journal)
    _append_journal_log("edit", jd)
    return jd, ""


def update_journal_metadata(journal_id: str, tags: str, category_id: str):
    try:
        journal = Journal.objects.get(id=journal_id)
    except Journal.DoesNotExist:
        return None, "凭证不存在。"

    tag_list = [x.strip() for x in (tags or "").split(",") if x.strip()]
    normalized_category_id = (category_id or "").strip() or None

    with transaction.atomic():
        journal.tags_raw = ",".join(tag_list)
        journal.save(update_fields=["tags_raw", "updated_at"])
        journal.entries.update(category_id=normalized_category_id)

    jd = _journal_to_dict(journal)
    _append_journal_log("edit_meta", jd)
    return jd, ""


def get_active_accounts():
    return [_account_to_dict(a) for a in Account.objects.filter(status="active")]


def create_account(
    name: str,
    account_type: str = "asset",
    currency: str = "CNY",
    opening_balance: str = "0",
    note: str = "",
):
    account_name = (name or "").strip()
    if not account_name:
        return None, "账户名称不能为空。"

    if Account.objects.filter(name=account_name).exists():
        return None, "账户名称已存在。"

    start = _to_decimal(opening_balance)
    account_id = str(uuid.uuid4())
    account = Account.objects.create(
        id=account_id,
        name=account_name,
        type=account_type or "asset",
        status="active",
        currency=(currency or "CNY").upper(),
        opening_balance=start,
        balance=start,
        note=note.strip(),
    )
    return _account_to_dict(account), ""


def account_used_count(account_id: str) -> int:
    from django.db.models import Q

    entries_count = JournalEntry.objects.filter(account_id=account_id).count()
    transfers_count = JournalTransfer.objects.filter(
        Q(from_account_id=account_id) | Q(to_account_id=account_id)
    ).count()
    return entries_count + transfers_count


def update_account(
    account_id: str, name: str, account_type: str, currency: str = "CNY", note: str = ""
):
    if not name or not name.strip():
        return False, "账户名称不能为空。"
    try:
        acc = Account.objects.get(id=account_id)
        acc.name = name.strip()
        if account_type in ("asset", "liability", "income", "expense"):
            acc.type = account_type
        if currency:
            acc.currency = currency.upper()
        acc.note = note.strip()
        acc.save()
        return True, ""
    except Account.DoesNotExist:
        return False, "账户不存在。"


def set_account_status(account_id: str, status: str):
    if account_id in PROTECTED_ACCOUNT_IDS and status != "active":
        return False, "系统账户不能停用。"
    try:
        acc = Account.objects.get(id=account_id)
        acc.status = status
        acc.save()
        return True, ""
    except Account.DoesNotExist:
        return False, "账户不存在。"


def delete_account(account_id: str):
    if account_id in PROTECTED_ACCOUNT_IDS:
        return False, "系统账户不能删除。"
    try:
        if account_used_count(account_id) > 0:
            return False, "已有记账记录"
        with transaction.atomic():
            Account.objects.get(id=account_id).delete()
        return True, ""
    except Account.DoesNotExist:
        return False, "账户不存在。"


def set_account_balance(account_id: str, balance: str):
    try:
        with transaction.atomic():
            acc = Account.objects.get(id=account_id)
            acc.opening_balance = _to_decimal(balance)
            acc.save()
            recalculate_account_balances()
        return True, ""
    except Account.DoesNotExist:
        return False, "账户不存在。"


def _entry_effect(account_type: str, debit: Decimal, credit: Decimal) -> Decimal:
    if account_type in {"asset", "expense"}:
        return debit - credit
    return credit - debit


def recalculate_account_balances(accounts=None):
    # This recalculates and updates the database.
    # To avoid many queries, we fetch all accounts, calculate, and bulk update.
    with transaction.atomic():
        accs = Account.objects.all()
        for acc in accs:
            acc.balance = acc.opening_balance

        acc_dict = {a.id: a for a in accs}

        journals = Journal.objects.order_by("date").prefetch_related("entries")
        for j in journals:
            for e in j.entries.all():
                if e.account_id in acc_dict:
                    effect = _entry_effect(
                        acc_dict[e.account_id].type, e.debit, e.credit
                    )
                    acc_dict[e.account_id].balance += effect

        Account.objects.bulk_update(accs, ["balance"])


def _append_journal_log(action: str, journal: dict):
    JournalLog.objects.create(
        timestamp=datetime.now(),
        action=action,
        journal_id=journal.get("id") or "",
        date=str(journal.get("date") or ""),
        description=journal.get("description") or "",
        entries=journal.get("entries", []),
    )


def list_journal_logs(limit: int = 200):
    rows = JournalLog.objects.order_by("-timestamp", "-id")[: max(1, int(limit or 200))]
    return [
        {
            "timestamp": row.timestamp.isoformat(timespec="seconds"),
            "action": row.action,
            "journal_id": row.journal_id,
            "date": row.date,
            "description": row.description,
            "entries": row.entries,
        }
        for row in rows
    ]


def list_all_tags() -> list:
    counts: dict[str, int] = {}
    for j in Journal.objects.all():
        for tag in j.get_tags():
            counts[tag] = counts.get(tag, 0) + 1
    return sorted(
        [{"tag": t, "count": c} for t, c in counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )


def rename_tag(old: str, new: str) -> int:
    count = 0
    with transaction.atomic():
        for j in Journal.objects.filter(tags_raw__contains=old):
            tags = j.get_tags()
            if old in tags:
                j.set_tags([new if t == old else t for t in tags])
                j.save()
                count += 1
    return count


def delete_tag(tag: str) -> int:
    count = 0
    with transaction.atomic():
        for j in Journal.objects.filter(tags_raw__contains=tag):
            tags = j.get_tags()
            if tag in tags:
                j.set_tags([t for t in tags if t != tag])
                j.save()
                count += 1
    return count
