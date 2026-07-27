#!/usr/bin/env python3
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "contracts/banking/integration-profiles.yaml"
PORTS = ROOT / "contracts/banking/ports.yaml"
MODELS = ROOT / "contracts/banking/canonical-models.yaml"
ERRORS = ROOT / "contracts/banking/error-contracts.yaml"


def load(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping")
    return data


def main():
    errors = []
    try:
        profiles = load(PROFILES)
        ports = load(PORTS)
        models = load(MODELS)
        error_contracts = load(ERRORS)

        for name, data in profiles.get("profiles", {}).items():
            for field in ("releaseClass", "providerMode", "dataClassification", "providers"):
                if field not in data:
                    errors.append(f"profile {name}: missing {field}")

        production = profiles.get("profiles", {}).get("production", {})
        forbidden = set(profiles.get("policy", {}).get("productionForbiddenProviders", []))
        if production.get("providerMode") != "real":
            errors.append("production providerMode must be real")
        if production.get("containsRealCustomerData") is not True:
            errors.append("production must declare real customer data")
        used = set(production.get("providers", {}).values())
        if used & forbidden:
            errors.append(f"production uses forbidden providers: {sorted(used & forbidden)}")

        port_ids = set()
        for port in ports.get("ports", []):
            port_id = port.get("id")
            if not port_id or port_id in port_ids:
                errors.append(f"port id missing/duplicate: {port_id}")
            port_ids.add(port_id)
            for field in ("owner", "consumer", "capability", "operations", "mockProvider", "productionProvider", "mutability"):
                if not port.get(field):
                    errors.append(f"port {port_id}: missing {field}")
            if port.get("mutability") == "transactional" and port.get("idempotency") != "required":
                errors.append(f"port {port_id}: transactional port must require idempotency")
            if port.get("mockProvider") == port.get("productionProvider"):
                errors.append(f"port {port_id}: mock and production providers must differ")

        required_models = {"Money", "CustomerReference", "DebtContract", "EligibilityDecision", "NegotiationOffer", "Agreement", "CardLimit", "CardInvoice"}
        actual_models = set(models.get("models", {}))
        if not required_models.issubset(actual_models):
            errors.append(f"canonical models missing: {sorted(required_models - actual_models)}")

        codes = set()
        for item in error_contracts.get("errors", []):
            code = item.get("code")
            if not code or code in codes:
                errors.append(f"error code missing/duplicate: {code}")
            codes.add(code)
            if "retryable" not in item or not item.get("category"):
                errors.append(f"error {code}: missing category/retryable")

        for doc in (ROOT / "docs/integration/banking-core-readiness.md", ROOT / "docs/integration/core-onboarding-checklist.md"):
            if not doc.exists():
                errors.append(f"missing documentation: {doc.relative_to(ROOT)}")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors.append(str(exc))

    if errors:
        print("Banking integration validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("OK: banking integration profiles, ports, models and errors are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
