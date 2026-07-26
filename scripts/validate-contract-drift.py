#!/usr/bin/env python3
"""Fail CI when Docker Compose and canonical architecture contracts diverge."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

INFRA_SERVICES = {
    "postgres",
    "mongodb",
    "redis",
    "kafka",
    "kafka-init",
    "opensearch",
    "jaeger",
    "loki",
    "promtail",
    "alloy",
    "prometheus",
    "grafana",
}

DATASTORE_ROWS = {
    "kafka": "Kafka",
    "postgres": "PostgreSQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "opensearch": "OpenSearch",
}


def fail(messages: list[str]) -> None:
    for message in messages:
        print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def parse_service_table(markdown: str) -> set[str]:
    section = markdown.split("## Serviços implementados", 1)[1]
    section = section.split("## Sistemas somente da arquitetura-alvo", 1)[0]
    services: set[str] = set()
    for line in section.splitlines():
        match = re.match(r"^\|\s*`?([a-z0-9][a-z0-9-]+)`?\s*\|", line)
        if match and match.group(1) not in {"serviço", "service"}:
            services.add(match.group(1))
    return services


def parse_documented_topics(markdown: str) -> set[str]:
    topics = set(re.findall(r"^\|\s*`([a-z0-9_.-]+)`\s*\|", markdown, flags=re.MULTILINE))
    return {topic for topic in topics if "." in topic}


def parse_compose_topics(compose: dict[str, Any]) -> set[str]:
    command = compose.get("services", {}).get("kafka-init", {}).get("command", "")
    if isinstance(command, list):
        command = " ".join(str(item) for item in command)
    return set(re.findall(r"\b(?:channel|intent|conversation|agent|tool)\.[a-z0-9_.-]+\b", str(command)))


def published_ports(service: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for item in service.get("ports", []) or []:
        if isinstance(item, dict):
            for key in ("published", "target"):
                if item.get(key) is not None:
                    result.add(str(item[key]))
        elif isinstance(item, str):
            parts = item.split(":")
            for part in parts[-2:]:
                value = part.split("/")[0]
                if value.isdigit():
                    result.add(value)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("compose_json", type=Path)
    args = parser.parse_args()

    compose = json.loads(args.compose_json.read_text(encoding="utf-8"))
    services = compose.get("services", {})
    if not isinstance(services, dict):
        fail(["docker compose config não retornou um objeto services válido"])

    errors: list[str] = []

    documented_services = parse_service_table(read_text("docs/contracts/services-map.md"))
    compose_apps = set(services) - INFRA_SERVICES
    if documented_services != compose_apps:
        missing_docs = sorted(compose_apps - documented_services)
        missing_compose = sorted(documented_services - compose_apps)
        if missing_docs:
            errors.append(f"serviços presentes no Compose e ausentes no mapa: {missing_docs}")
        if missing_compose:
            errors.append(f"serviços documentados e ausentes no Compose: {missing_compose}")

    compose_topics = parse_compose_topics(compose)
    documented_topics = parse_documented_topics(read_text("docs/contracts/kafka-events.md"))
    if compose_topics != documented_topics:
        errors.append(
            "tópicos Kafka divergentes: "
            f"somente Compose={sorted(compose_topics - documented_topics)}, "
            f"somente docs={sorted(documented_topics - compose_topics)}"
        )

    datastore_doc = read_text("docs/contracts/data-stores.md")
    for compose_name, display_name in DATASTORE_ROWS.items():
        if compose_name not in services:
            errors.append(f"datastore obrigatório ausente no Compose: {compose_name}")
        if not re.search(rf"^\|\s*{re.escape(display_name)}\s*\|", datastore_doc, flags=re.MULTILINE):
            errors.append(f"datastore ausente da matriz canônica: {display_name}")

    for service_name in sorted(compose_apps):
        page = ROOT / "docs" / "services" / f"{service_name}.md"
        if not page.exists():
            errors.append(f"página de serviço ausente: {page.relative_to(ROOT)}")
            continue
        page_text = page.read_text(encoding="utf-8")
        ports = published_ports(services[service_name])
        undocumented = sorted(port for port in ports if port not in page_text)
        if undocumented:
            errors.append(f"portas de {service_name} não encontradas na página do serviço: {undocumented}")

    stale_markers = {
        "README.md": ["7 tópicos existem hoje"],
        "docs/contracts/services-map.md": ["sem repo próprio — pasta local"],
        "docs/security/security-architecture.md": ["sem emitir nenhum token"],
    }
    for relative, markers in stale_markers.items():
        text = read_text(relative)
        for marker in markers:
            if marker in text:
                errors.append(f"marcador obsoleto em {relative}: {marker!r}")

    if errors:
        fail(errors)

    print(
        f"Contratos sincronizados: {len(compose_apps)} serviços, "
        f"{len(compose_topics)} tópicos e {len(DATASTORE_ROWS)} datastores."
    )


if __name__ == "__main__":
    main()
