#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8700"
TENANT = "00000000-0000-0000-0000-000000000001"


def request_json(path: str, payload: dict | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method="GET" if payload is None else "POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def issue(client_id: str, audience: str) -> str:
    status, body = request_json(
        "/token",
        {"client_id": client_id, "audience": audience, "tenant_id": TENANT, "ttl_seconds": 120},
    )
    if status != 200:
        raise AssertionError(f"token issue failed: {status} {body}")
    return body["access_token"]


def authorize(token: str, action: str, resource: str, context: dict | None = None, tenant: str = TENANT) -> tuple[int, dict]:
    return request_json(
        "/authorize",
        {
            "audience": "core-bancario-mock",
            "tenant_id": tenant,
            "action": action,
            "resource": resource,
            "context": context or {},
        },
        {"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant},
    )


def main() -> int:
    status, discovery = request_json("/.well-known/openid-configuration")
    assert status == 200 and discovery["jwks_uri"].endswith("/jwks.json")
    status, jwks = request_json("/jwks.json")
    assert status == 200 and len(jwks["keys"]) == 1 and jwks["keys"][0]["alg"] == "RS256"

    token = issue("renegotiation-service", "core-bancario-mock")
    status, decision = authorize(token, "consultar_cliente", "/clients/11111111111")
    assert status == 200 and decision["allowed"] is True

    status, denied = authorize(token, "confirmar_acordo", "/simulations/sim-1/confirmations")
    assert status == 403 and denied["detail"] == "policy_denied"

    evidence = {"policy_id": "policy-1", "message_id": "message-1", "confirmation_message_id": "message-1"}
    status, decision = authorize(token, "confirmar_acordo", "/simulations/sim-1/confirmations", evidence)
    assert status == 200 and decision["allowed"] is True

    status, body = request_json(
        "/token",
        {"client_id": "knowledge-service", "audience": "core-bancario-mock", "tenant_id": TENANT},
    )
    assert status == 403 and body["detail"] == "workload_pair_not_allowed"

    other_tenant = "00000000-0000-0000-0000-000000000002"
    status, body = authorize(token, "consultar_cliente", "/clients/11111111111", tenant=other_tenant)
    assert status in (401, 403)

    print("OK: RS256 issuance, JWKS discovery, workload pair enforcement and OPA decisions validated")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
