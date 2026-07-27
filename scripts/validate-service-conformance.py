#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PLATFORM_ROOT / "release/release-manifest.yaml"
POLICY_CONTRACT = PLATFORM_ROOT / "contracts/policy/authorization.yaml"
SERVICES_MAP = PLATFORM_ROOT / "docs/contracts/services-map.md"


def fail(message: str) -> None:
    raise ValueError(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a service repository against platform governance contracts.")
    parser.add_argument("--service", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()

    try:
        manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        repositories = manifest.get("repositories", [])
        matches = [item for item in repositories if item.get("name") == args.service]
        if len(matches) != 1:
            fail(f"service {args.service!r} must occur exactly once in release manifest")
        if matches[0].get("repository") != args.repository:
            fail(
                f"repository mismatch for {args.service}: expected {matches[0].get('repository')}, "
                f"got {args.repository}"
            )

        root = args.root.resolve()
        if not (root / "Dockerfile").is_file():
            fail("Dockerfile is required for attested OCI evidence")
        workflows = root / ".github/workflows"
        if not workflows.is_dir() or not any(workflows.glob("*.y*ml")):
            fail("at least one GitHub Actions workflow is required")
        supply_chain = workflows / "supply-chain.yml"
        if not supply_chain.is_file():
            fail(".github/workflows/supply-chain.yml is required")

        services_map = SERVICES_MAP.read_text(encoding="utf-8")
        if args.service not in services_map:
            fail(f"{args.service} is missing from canonical services map")

        policy_text = POLICY_CONTRACT.read_text(encoding="utf-8")
        if args.service not in policy_text and matches[0].get("role") not in {"architecture", "external-system-mock"}:
            fail(f"{args.service} is not referenced by the executable authorization contract")

        workflow_text = supply_chain.read_text(encoding="utf-8")
        required_tokens = [
            "reusable-service-supply-chain.yml@main",
            f"service_name: {args.service}",
        ]
        for token in required_tokens:
            if token not in workflow_text:
                fail(f"supply-chain caller is missing {token!r}")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"OK: {args.service} conforms to the platform governance baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
