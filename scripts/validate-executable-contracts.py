#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release/release-manifest.yaml"
OPENAPI = ROOT / "contracts/openapi/internal-platform.yaml"
ASYNCAPI = ROOT / "contracts/asyncapi/platform-events.yaml"
AUTHZ = ROOT / "contracts/policy/authorization.yaml"
COMPOSE_OVERRIDE = ROOT / "docker-compose.override.yml"

EXPECTED_REPOSITORIES = {
    "conversational-ai-platform-architecture",
    "whatsapp-bff",
    "conversation-orchestrator",
    "agent-runtime-renegotiation",
    "tool-service-renegotiation",
    "renegotiation-service",
    "agent-runtime-fatura-cartao",
    "tool-service-cartao-credito",
    "knowledge-service",
    "conversation-memory-service",
    "conversation-audit-service",
    "conversation-handoff-service",
    "core-bancario-mock",
}
EXPECTED_TOPICS = {
    "channel.webhook.received",
    "channel.webhook.received.retry",
    "channel.webhook.received.dlq",
    "channel.message.received",
    "channel.message.status",
    "intent.detected",
    "conversation.state_changed",
    "agent.events",
    "tool.executed",
}
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping")
    return data


def parameter_names(operation: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for parameter in operation.get("parameters", []):
        if "$ref" in parameter:
            names.add(parameter["$ref"].split("/")[-1])
        elif isinstance(parameter.get("name"), str):
            names.add(parameter["name"])
    return names


def validate_manifest(errors: list[str]) -> set[str]:
    data = load(MANIFEST)
    if data.get("schemaVersion") != 1:
        errors.append("release manifest schemaVersion must be 1")
    repositories = data.get("repositories", [])
    names = {item.get("name") for item in repositories if isinstance(item, dict)}
    if names != EXPECTED_REPOSITORIES:
        errors.append(f"release manifest repositories differ: missing={sorted(EXPECTED_REPOSITORIES - names)}, extra={sorted(names - EXPECTED_REPOSITORIES)}")
    for item in repositories:
        for field in ("repository", "path", "ref", "role"):
            if not item.get(field):
                errors.append(f"release manifest {item.get('name')}: missing {field}")
    if data.get("policy", {}).get("requiredRepositoryCount") != len(EXPECTED_REPOSITORIES):
        errors.append("release manifest requiredRepositoryCount is stale")
    return names


def validate_openapi(errors: list[str], repositories: set[str]) -> None:
    data = load(OPENAPI)
    if not str(data.get("openapi", "")).startswith("3.1"):
        errors.append("OpenAPI contract must use 3.1")
    operation_ids: set[str] = set()
    operations = 0
    for path, path_item in data.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            operations += 1
            operation_id = operation.get("operationId")
            if not operation_id:
                errors.append(f"OpenAPI {method.upper()} {path}: operationId missing")
            elif operation_id in operation_ids:
                errors.append(f"OpenAPI duplicate operationId: {operation_id}")
            else:
                operation_ids.add(operation_id)
            services = str(operation.get("x-service", "")).split("|")
            for service in services:
                if service and service not in repositories:
                    errors.append(f"OpenAPI {operation_id}: unknown provider {service}")
            caller = operation.get("x-caller")
            if caller and caller not in repositories:
                errors.append(f"OpenAPI {operation_id}: unknown caller {caller}")
            names = parameter_names(operation)
            if operation.get("x-internal-auth"):
                if "Authorization" not in names or "TenantId" not in names:
                    errors.append(f"OpenAPI {operation_id}: internal operation lacks auth/tenant headers")
            if operation.get("x-idempotent") and "IdempotencyKey" not in names:
                errors.append(f"OpenAPI {operation_id}: idempotent operation lacks Idempotency-Key")
            if method in {"post", "put", "patch"} and operation.get("x-idempotent") is None and operation.get("x-service") == "core-bancario-mock":
                errors.append(f"OpenAPI {operation_id}: mutable Core operation must declare x-idempotent")
    if operations < 7:
        errors.append(f"OpenAPI contract is unexpectedly small: {operations} operations")


def validate_asyncapi(errors: list[str]) -> None:
    data = load(ASYNCAPI)
    if not str(data.get("asyncapi", "")).startswith("3.0"):
        errors.append("AsyncAPI contract must use 3.0")
    channels = data.get("channels", {})
    addresses = {item.get("address") for item in channels.values() if isinstance(item, dict)}
    if addresses != EXPECTED_TOPICS:
        errors.append(f"AsyncAPI topics differ: missing={sorted(EXPECTED_TOPICS - addresses)}, extra={sorted(addresses - EXPECTED_TOPICS)}")
    compose_text = COMPOSE_OVERRIDE.read_text(encoding="utf-8")
    compose_topics = set(re.findall(r"(?:^|\s)(channel\.[\w.]+|intent\.detected|conversation\.state_changed|agent\.events|tool\.executed)(?:\s|$)", compose_text))
    if not EXPECTED_TOPICS.issubset(compose_topics):
        errors.append(f"Compose kafka-init lacks topics: {sorted(EXPECTED_TOPICS - compose_topics)}")


def validate_policy(errors: list[str], repositories: set[str]) -> None:
    data = load(AUTHZ)
    if data.get("schemaVersion") != 1:
        errors.append("authorization contract schemaVersion must be 1")
    rule_ids: set[str] = set()
    for rule in data.get("rules", []):
        rule_id = rule.get("id")
        if not rule_id or rule_id in rule_ids:
            errors.append(f"authorization rule id missing/duplicate: {rule_id}")
        rule_ids.add(rule_id)
        for field in ("caller", "audience"):
            value = rule.get(field)
            if value not in repositories:
                errors.append(f"authorization rule {rule_id}: unknown {field} {value}")
        methods = rule.get("methods", [])
        if not methods or any(method not in {"GET", "POST", "PUT", "PATCH", "DELETE"} for method in methods):
            errors.append(f"authorization rule {rule_id}: invalid methods")
        if rule.get("idempotency") == "required_for_post" and "POST" not in methods:
            errors.append(f"authorization rule {rule_id}: requires idempotency but has no POST")


def main() -> int:
    errors: list[str] = []
    try:
        repositories = validate_manifest(errors)
        validate_openapi(errors, repositories)
        validate_asyncapi(errors)
        validate_policy(errors, repositories)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors.append(str(exc))
    if errors:
        print("Executable contract validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("OK: release, HTTP, Kafka and authorization contracts are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
