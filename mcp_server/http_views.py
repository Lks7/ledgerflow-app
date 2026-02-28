import json
import os

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .server import handle_jsonrpc_request


def _is_authorized(request) -> bool:
    expected = (os.environ.get("MCP_API_TOKEN") or "").strip()
    if not expected:
        # If token is not set, allow access (for local/dev).
        return True

    auth = (request.headers.get("Authorization") or "").strip()
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
        return token == expected

    header_token = (request.headers.get("X-MCP-Token") or "").strip()
    return header_token == expected


@csrf_exempt
def mcp_http(request):
    if request.method != "POST":
        return JsonResponse({"error": "only POST is supported"}, status=405)

    if not _is_authorized(request):
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "invalid json body"}, status=400)

    # Support batch requests
    if isinstance(payload, list):
        responses = []
        for item in payload:
            resp = handle_jsonrpc_request(item)
            if resp is not None:
                responses.append(resp)
        if not responses:
            return HttpResponse(status=204)
        return JsonResponse(responses, safe=False)

    resp = handle_jsonrpc_request(payload)
    if resp is None:
        return HttpResponse(status=204)
    return JsonResponse(resp)
