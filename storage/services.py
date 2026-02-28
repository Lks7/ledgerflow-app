import hashlib
import json
from typing import Callable

from django.db import IntegrityError, transaction

from .models import IdempotencyRecord


def _stable_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def run_with_idempotency(
    *,
    tool_name: str,
    idempotency_key: str,
    args_for_hash: dict,
    runner: Callable[[], dict],
) -> dict:
    """Execute runner once for a (tool_name, key) pair.

    - If key does not exist: execute runner and persist response.
    - If key exists and args hash matches: return persisted response.
    - If key exists and args hash differs: return conflict response.
    """

    args_hash = _stable_hash(args_for_hash or {})

    existing = IdempotencyRecord.objects.filter(
        tool_name=tool_name, idempotency_key=idempotency_key
    ).first()
    if existing:
        if existing.args_hash != args_hash:
            return {
                "ok": False,
                "error": "idempotency_key already used with different arguments",
                "idempotency_replay": False,
            }
        replay = dict(existing.response_payload or {})
        replay["idempotency_replay"] = True
        return replay

    result = runner()
    payload = dict(result or {})

    try:
        with transaction.atomic():
            IdempotencyRecord.objects.create(
                tool_name=tool_name,
                idempotency_key=idempotency_key,
                args_hash=args_hash,
                response_payload=payload,
            )
    except IntegrityError:
        # concurrent duplicate request; fetch winner and return
        again = IdempotencyRecord.objects.filter(
            tool_name=tool_name, idempotency_key=idempotency_key
        ).first()
        if again and again.args_hash == args_hash:
            replay = dict(again.response_payload or {})
            replay["idempotency_replay"] = True
            return replay
        return {
            "ok": False,
            "error": "idempotency conflict",
            "idempotency_replay": False,
        }

    payload["idempotency_replay"] = False
    return payload
