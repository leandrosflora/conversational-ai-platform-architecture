#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8700"
TENANT = "00000000-0000-0000-0000-000000000001"
BOOTSTRAP_SECRETS = {
    "renegotiation-service": "local-renegotiation-service-bootstrap-secret-06",
    "knowledge-service": "not-configured-because-this-workload-cannot-issue",
}


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


def issue(client_id: str, audience: str, secret: str | None = None) -> tuple[int, dict]:
    headers = {}
    if secret is not None:
        headers["X-Workload-Bootstrap-Token"] = secret
    return request_json(
        "/token",
        {"client_id": client_id, "audience": audience, "tenant_id": TENANT, "ttl_seconds": 120},
        headers,
    )


def require_token(client_id: str, audience: str) -> str:
    status, body = issue(client_id, audience, BOOTSTRAP_SECRETS[client_id])
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
    status, readiness = request_json("/health/ready")
    assert status == 200 and readiness["bootstrapWorkloads"] == 7

    status, discovery = request_json("/.well-known/openid-configuration")
    assert status == 200 and discovery["jwks_uri"].endswith("/jwks.json")
    assert discovery["token_endpoint_auth_methods_supported"] == ["x-workload-bootstrap-token"]
    status, jwks = request_json("/jwks.json")
    assert status == 200 and len(jwks["keys"]) == 1 and jwks["keys"][0]["alg"] == "RS256"

    status, body = issue("renegotiation-service", "core-bancario-mock")
    assert status == 401 and body["detail"] == "workload_bootstrap_authentication_required"
    status, body = issue("renegotiation-service", "core-bancario-mock", "wrong-bootstrap-secret-with-at-least-32-bytes")
    assert status == 401 and body["detail"] == "workload_bootstrap_authentication_failed"

    token = require_token("renegotiation-service", "core-bancario-mock")
    status, decision = authorize(token, "consultar_cliente", "/clients/11111111111")
    assert status == 200 and decision["allowed"] is True

    status, denied = authorize(token, "confirmar_acordo", "/simulations/sim-1/confirmations")
    assert status == 403 and denied["detail"] == "policy_denied"

    evidence = {"policy_id": "policy-1", "message_id": "message-1", "confirmation_message_id": "message-1"}
    status, decision = authorize(token, "confirmar_acordo", "/simulations/sim-1/confirmations", evidence)
    assert status == 200 and decision["allowed"] is True

    status, body = issue(
        "knowledge-service",
        "core-bancario-mock",
        BOOTSTRAP_SECRETS["knowledge-service"],
    )
    assert status == 401 and body["detail"] in {
        "workload_bootstrap_authentication_required",
        "workload_bootstrap_authentication_failed",
    }

    other_tenant = "00000000-0000-0000-0000-000000000002"
    status, body = authorize(token, "consultar_cliente", "/clients/11111111111", tenant=other_tenant)
    assert status in (401, 403)

    print("OK: authenticated RS256 issuance, JWKS, workload pairs and OPA decisions validated")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
