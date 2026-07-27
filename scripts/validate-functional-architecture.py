#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
FUNCTIONAL = ROOT / "contracts/functional"
MANIFEST = ROOT / "release/release-manifest.yaml"

FILES = {
    "capabilities": FUNCTIONAL / "capabilities.yaml",
    "domains": FUNCTIONAL / "domains.yaml",
    "skills": FUNCTIONAL / "skills.yaml",
    "journeys": FUNCTIONAL / "journeys.yaml",
    "events": FUNCTIONAL / "business-events.yaml",
    "kpis": FUNCTIONAL / "kpis.yaml",
}

REQUIRED_DOCS = {
    ROOT / "docs/functional/capability-map.md",
    ROOT / "docs/functional/domain-map.md",
    ROOT / "docs/functional/skill-contract.md",
    ROOT / "docs/functional/journey-state-contracts.md",
    ROOT / "docs/functional/business-events-catalog.md",
    ROOT / "docs/functional/handoff-case-lifecycle.md",
    ROOT / "docs/functional/customer-identity-context.md",
    ROOT / "docs/functional/knowledge-governance.md",
    ROOT / "docs/functional/business-kpi-map.md",
    ROOT / "docs/functional/traceability-matrix.md",
}

ASSURANCE_LEVELS = {"anonymous", "identified", "verified", "strong_authenticated"}
OPERATION_MODES = {"read_only", "transactional"}
DOMAIN_TYPES = {"core", "supporting", "generic", "external"}
MATURITY = {"implemented", "partial", "target"}


def load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping")
    if data.get("schemaVersion") != 1:
        raise ValueError(f"{path}: schemaVersion must be 1")
    return data


def unique_ids(items: list[Any], label: str, errors: list[str]) -> set[str]:
    ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"{label}: every item must be a mapping")
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            errors.append(f"{label}: item without id")
            continue
        if item_id in ids:
            errors.append(f"{label}: duplicate id {item_id}")
        ids.add(item_id)
    return ids


def repository_names() -> set[str]:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return {
        item["name"]
        for item in manifest.get("repositories", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }


def validate() -> list[str]:
    errors: list[str] = []
    data = {name: load(path) for name, path in FILES.items()}
    repositories = repository_names()

    capabilities = data["capabilities"].get("capabilities", [])
    capability_ids = unique_ids(capabilities, "capabilities", errors)
    for capability in capabilities:
        if not isinstance(capability, dict):
            continue
        if capability.get("level") not in {1, 2, 3}:
            errors.append(f"capability {capability.get('id')}: invalid level")
        parent = capability.get("parent")
        if capability.get("level", 1) > 1 and parent not in capability_ids:
            errors.append(f"capability {capability.get('id')}: unknown parent {parent}")
        if capability.get("maturity") not in MATURITY:
            errors.append(f"capability {capability.get('id')}: invalid maturity")
        for service in capability.get("services", []):
            if service not in repositories:
                errors.append(f"capability {capability.get('id')}: unknown service {service}")

    domains = data["domains"].get("domains", [])
    domain_ids = unique_ids(domains, "domains", errors)
    for domain in domains:
        if not isinstance(domain, dict):
            continue
        if domain.get("type") not in DOMAIN_TYPES:
            errors.append(f"domain {domain.get('id')}: invalid type")
        for capability in domain.get("capabilities", []):
            if capability not in capability_ids:
                errors.append(f"domain {domain.get('id')}: unknown capability {capability}")
        for service in domain.get("services", []):
            if service not in repositories:
                errors.append(f"domain {domain.get('id')}: unknown service {service}")
    for relation in data["domains"].get("relationships", []):
        if relation.get("upstream") not in domain_ids or relation.get("downstream") not in domain_ids:
            errors.append(f"domain relationship references unknown domain: {relation}")

    events = data["events"].get("events", [])
    event_ids = unique_ids(events, "business events", errors)
    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("domain") not in domain_ids:
            errors.append(f"event {event.get('id')}: unknown domain {event.get('domain')}")
        if event.get("producer") not in repositories:
            errors.append(f"event {event.get('id')}: unknown producer {event.get('producer')}")
        for consumer in event.get("consumers", []):
            if consumer not in repositories:
                errors.append(f"event {event.get('id')}: unknown consumer {consumer}")
    required_envelope = set(data["events"].get("requiredEnvelopeFields", []))
    mandatory_envelope = {"eventId", "eventType", "occurredAt", "tenantId", "journeyId", "skillId", "correlationId"}
    if not mandatory_envelope.issubset(required_envelope):
        errors.append(f"business events: missing envelope fields {sorted(mandatory_envelope - required_envelope)}")

    kpis = data["kpis"].get("kpis", [])
    kpi_ids = unique_ids(kpis, "kpis", errors)
    for kpi in kpis:
        if not isinstance(kpi, dict):
            continue
        if not kpi.get("formula") or not kpi.get("owner"):
            errors.append(f"kpi {kpi.get('id')}: formula and owner are required")
        for event in kpi.get("sourceEvents", []):
            if event not in event_ids:
                errors.append(f"kpi {kpi.get('id')}: unknown source event {event}")

    skills = data["skills"].get("skills", [])
    skill_ids = unique_ids(skills, "skills", errors)
    skill_by_id = {skill.get("id"): skill for skill in skills if isinstance(skill, dict)}
    for skill in skills:
        if not isinstance(skill, dict):
            continue
        skill_id = skill.get("id")
        if skill.get("domain") not in domain_ids:
            errors.append(f"skill {skill_id}: unknown domain {skill.get('domain')}")
        if skill.get("runtimeService") not in repositories:
            errors.append(f"skill {skill_id}: unknown runtimeService {skill.get('runtimeService')}")
        if skill.get("operationMode") not in OPERATION_MODES:
            errors.append(f"skill {skill_id}: invalid operationMode")
        if skill.get("requiredAssuranceLevel") not in ASSURANCE_LEVELS:
            errors.append(f"skill {skill_id}: invalid requiredAssuranceLevel")
        for capability in skill.get("capabilities", []):
            if capability not in capability_ids:
                errors.append(f"skill {skill_id}: unknown capability {capability}")
        for tool in skill.get("tools", []):
            if tool.get("service") not in repositories:
                errors.append(f"skill {skill_id}: tool {tool.get('id')} uses unknown service")
            if skill.get("operationMode") == "read_only" and tool.get("mutating") is True:
                errors.append(f"skill {skill_id}: read_only skill has mutating tool {tool.get('id')}")
        for kpi in skill.get("kpis", []):
            if kpi not in kpi_ids:
                errors.append(f"skill {skill_id}: unknown kpi {kpi}")

    journeys = data["journeys"].get("journeys", [])
    journey_skill_ids: set[str] = set()
    for journey in journeys:
        if not isinstance(journey, dict):
            errors.append("journeys: every item must be a mapping")
            continue
        skill_id = journey.get("skillId")
        if skill_id not in skill_ids:
            errors.append(f"journey: unknown skill {skill_id}")
            continue
        if skill_id in journey_skill_ids:
            errors.append(f"journey: duplicate contract for skill {skill_id}")
        journey_skill_ids.add(skill_id)
        states = journey.get("states", [])
        state_ids = unique_ids(states, f"journey {skill_id} states", errors)
        if journey.get("initialState") not in state_ids:
            errors.append(f"journey {skill_id}: initialState is unknown")
        skill = skill_by_id[skill_id]
        if skill.get("initialState") != journey.get("initialState"):
            errors.append(f"journey {skill_id}: skill and journey initialState differ")
        for terminal in skill.get("terminalStates", []):
            if terminal not in state_ids:
                errors.append(f"journey {skill_id}: terminal state {terminal} is unknown")
        for state in states:
            fields = state.get("requiredFields", [])
            if not isinstance(fields, list) or any(not isinstance(field, str) for field in fields):
                errors.append(f"journey {skill_id}: invalid requiredFields in {state.get('id')}")
        for transition in journey.get("transitions", []):
            for source in transition.get("from", []):
                if source not in state_ids:
                    errors.append(f"journey {skill_id}: transition from unknown state {source}")
            if transition.get("to") not in state_ids:
                errors.append(f"journey {skill_id}: transition to unknown state {transition.get('to')}")
            if transition.get("event") not in event_ids:
                errors.append(f"journey {skill_id}: transition uses unknown event {transition.get('event')}")

    if journey_skill_ids != skill_ids:
        errors.append(f"journeys do not cover all skills: missing={sorted(skill_ids - journey_skill_ids)}")

    for path in REQUIRED_DOCS:
        if not path.is_file():
            errors.append(f"missing functional documentation: {path.relative_to(ROOT)}")

    return errors


def main() -> int:
    try:
        errors = validate()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors = [str(exc)]
    if errors:
        print("Functional architecture validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("OK: capabilities, domains, skills, journeys, business events and KPIs are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
