import json
import os
import sys
import traceback
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
from lists.services import (  # noqa: E402
    add_item,
    delete_item,
    list_items,
    pending_summary,
    update_item,
    update_status,
)


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
    month = _required(args, "month")
    tag = (args.get("tag") or "").strip()
    return {"ok": True, "journals": list_journals(month=month, tag=tag)}


def tool_ledger_get_journal(args: dict) -> dict:
    month = _required(args, "month")
    journal_id = _required(args, "journal_id")
    j = get_journal(month, journal_id)
    if not j:
        return {"ok": False, "error": "journal not found"}
    return {"ok": True, "journal": j}


def tool_ledger_create_journal(args: dict) -> dict:
    date = _required(args, "date")
    description = _required(args, "description")
    source = args.get("source", "mcp")
    tags = args.get("tags", "")
    entries = args.get("entries", [])
    transfer_lines = args.get("transfer_lines", [])

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
    name = _required(args, "name")
    qty = args.get("qty", 1)
    est_price = args.get("est_price", 0)
    actual_price = args.get("actual_price", 0)
    priority = args.get("priority", "normal")
    planned_date = args.get("planned_date", "")
    platform = args.get("platform", "")
    note = args.get("note", "")

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
            "description": "List journals by month and optional tag",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "month": {"type": "string", "description": "YYYY-MM"},
                    "tag": {"type": "string"},
                },
                "required": ["month"],
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
                    "entries": {"type": "array"},
                    "transfer_lines": {"type": "array"},
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
                    "entries": {"type": "array"},
                    "transfer_lines": {"type": "array"},
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
}


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
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": [meta for meta, _fn in TOOLS.values()]},
        }

    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name not in TOOLS:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": _err(f"unknown tool: {name}"),
            }
        _meta, fn = TOOLS[name]
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
