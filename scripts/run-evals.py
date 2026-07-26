#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "evals/scenarios.yaml"
DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"
RUNTIMES = {
    "agent-runtime-renegotiation": {
        "url": "http://localhost:8100/process",
        "secret_env": "INTERNAL_AUTH_SECRET_CONVERSATION_ORCHESTRATOR__AGENT_RUNTIME_RENEGOTIATION",
    },
    "agent-runtime-fatura-cartao": {
        "url": "http://localhost:8110/process",
        "secret_env": "INTERNAL_AUTH_SECRET_CONVERSATION_ORCHESTRATOR__AGENT_RUNTIME_FATURA_CARTAO",
    },
}


def b64url(raw: bytes) -> bytes:
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def issue_token(audience: str, secret: str, tenant: str) -> str:
    now = int(time.time())
    caller = "conversation-orchestrator"
    header = {"alg": "HS256", "typ": "JWT", "kid": caller}
    payload = {
        "iss": "conversational-ai-platform",
        "sub": caller,
        "aud": audience,
        "iat": now,
        "nbf": now - 1,
        "exp": now + 300,
        "jti": uuid.uuid4().hex,
        "tenant_id": tenant,
    }
    signing_input = b".".join(
        [
            b64url(json.dumps(header, separators=(",", ":")).encode()),
            b64url(json.dumps(payload, separators=(",", ":")).encode()),
        ]
    )
    signature = b64url(hmac.new(secret.encode(), signing_input, hashlib.sha256).digest())
    return (signing_input + b"." + signature).decode()


def offline_decision(runtime: str, text: str) -> dict[str, Any]:
    normalized = text.lower()
    if any(keyword in normalized for keyword in ("atendente", "humano", "pessoa real")):
        return {
            "Intent": "human_handoff_request",
            "RequiresHandoff": True,
            "HandoffReason": "customer_requested_human",
            "OutOfScope": False,
        }
    if runtime == "agent-runtime-renegotiation":
        if "renegoc" in normalized:
            intent = "renegotiation_request"
        elif any(keyword in normalized for keyword in ("divida", "dívida", "debito", "débito", "boleto", "parcela")):
            intent = "debt_inquiry"
        else:
            intent = "greeting"
        return {"Intent": intent, "RequiresHandoff": False, "HandoffReason": None, "OutOfScope": False}
    if any(keyword in normalized for keyword in ("renegoc", "divida", "dívida", "pix", "boleto", "recarga")):
        return {"Intent": "out_of_scope", "RequiresHandoff": False, "HandoffReason": None, "OutOfScope": True}
    if "limite" in normalized:
        intent = "consultar_limite"
    elif "fatura" in normalized or "conta do cartao" in normalized:
        intent = "consultar_fatura"
    else:
        intent = "greeting"
    return {"Intent": intent, "RequiresHandoff": False, "HandoffReason": None, "OutOfScope": False}


def online_decision(runtime: str, scenario_id: str, text: str, tenant: str) -> tuple[dict[str, Any], float]:
    config = RUNTIMES[runtime]
    secret = os.getenv(config["secret_env"])
    if not secret or len(secret.encode()) < 32:
        raise RuntimeError(f"missing or short secret: {config['secret_env']}")
    token = issue_token(runtime, secret, tenant)
    payload = {
        "TenantId": tenant,
        "ConversationId": f"eval-{scenario_id}",
        "MessageId": f"eval-{scenario_id}-{uuid.uuid4().hex[:8]}",
        "MessageType": "text",
        "Text": text,
        "State": "Started",
        "JourneyVersion": 0,
        "LastIntent": None,
        "StructuredState": None,
        "SessionReset": False,
    }
    request = urllib.request.Request(
        config["url"],
        method="POST",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "X-Tenant-Id": tenant,
        },
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{runtime} returned {exc.code}: {exc.read().decode(errors='replace')}") from exc
    return data, (time.perf_counter() - started) * 1000


def compare(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    mapping = {
        "intent": "Intent",
        "requiresHandoff": "RequiresHandoff",
        "handoffReason": "HandoffReason",
        "outOfScope": "OutOfScope",
    }
    errors: list[str] = []
    for expected_key, actual_key in mapping.items():
        if expected_key in expected and actual.get(actual_key) != expected[expected_key]:
            errors.append(f"{actual_key}: expected {expected[expected_key]!r}, got {actual.get(actual_key)!r}")
    forbidden = set(expected.get("forbiddenIntents", []))
    if actual.get("Intent") in forbidden:
        errors.append(f"forbidden intent returned: {actual.get('Intent')}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic conversational AI regression evals.")
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--mode", choices=("offline", "online"), default="offline")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--tenant", default=os.getenv("DEFAULT_TENANT_ID", DEFAULT_TENANT))
    args = parser.parse_args()

    suite = yaml.safe_load(args.suite.read_text(encoding="utf-8"))
    if suite.get("schemaVersion") != 1:
        raise SystemExit("unsupported eval schemaVersion")
    results: list[dict[str, Any]] = []
    failures = 0
    handoffs = 0
    for scenario in suite.get("scenarios", []):
        runtime = scenario["runtime"]
        started = time.perf_counter()
        try:
            if args.mode == "online":
                actual, latency_ms = online_decision(runtime, scenario["id"], scenario["text"], args.tenant)
            else:
                actual = offline_decision(runtime, scenario["text"])
                latency_ms = (time.perf_counter() - started) * 1000
            errors = compare(scenario["expected"], actual)
        except Exception as exc:  # one scenario must not hide the remaining evidence
            actual = {}
            latency_ms = (time.perf_counter() - started) * 1000
            errors = [str(exc)]
        if actual.get("RequiresHandoff"):
            handoffs += 1
        if errors:
            failures += 1
        results.append({
            "id": scenario["id"],
            "runtime": runtime,
            "passed": not errors,
            "latencyMs": round(latency_ms, 2),
            "errors": errors,
            "actual": actual,
        })
        print(f"{'PASS' if not errors else 'FAIL'} {scenario['id']} ({latency_ms:.1f} ms)")
        for error in errors:
            print(f"  - {error}")

    total = len(results)
    pass_rate = (total - failures) / total if total else 0.0
    handoff_rate = handoffs / total if total else 0.0
    thresholds = suite.get("thresholds", {})
    threshold_errors: list[str] = []
    if pass_rate < float(thresholds.get("passRate", 1.0)):
        threshold_errors.append(f"pass rate {pass_rate:.3f} below threshold")
    if handoff_rate > float(thresholds.get("maxHandoffRate", 1.0)):
        threshold_errors.append(f"handoff rate {handoff_rate:.3f} above threshold")
    max_latency = float(thresholds.get("maxLatencyMs", 1e12))
    if args.mode == "online" and any(result["latencyMs"] > max_latency for result in results):
        threshold_errors.append(f"one or more scenarios exceeded {max_latency} ms")

    report = {
        "schemaVersion": 1,
        "suite": suite.get("suite"),
        "mode": args.mode,
        "summary": {
            "total": total,
            "passed": total - failures,
            "failed": failures,
            "passRate": pass_rate,
            "handoffRate": handoff_rate,
            "thresholdErrors": threshold_errors,
        },
        "results": results,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures or threshold_errors:
        return 1
    print(f"OK: {total} eval scenarios passed; handoff rate={handoff_rate:.3f}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
