#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

CANONICAL_FILES = [
    Path("README.md"),
    Path("docs/index.md"),
    Path("docs/runbook.md"),
    Path("docs/security/security-architecture.md"),
    Path("docs/contracts/services-map.md"),
    Path("docs/services/core-bancario-mock.md"),
]

FORBIDDEN = {
    "agent/p0-consistency-policy": "branch transitório não deve aparecer em documentação canônica",
    "conversational-ai-demo-arch/": "use conversational-ai-platform-architecture/",
    "não há CI obrigatório, SAST, SCA, SBOM": "o repositório já possui CI, Trivy e SBOM",
    "ainda precisa receber um workflow de CI": "core-bancario-mock já possui workflow de CI",
}

errors: list[str] = []
for path in CANONICAL_FILES:
    if not path.exists():
        errors.append(f"{path}: arquivo canônico ausente")
        continue
    text = path.read_text(encoding="utf-8")
    for token, reason in FORBIDDEN.items():
        if token in text:
            errors.append(f"{path}: referência obsoleta {token!r} ({reason})")

if errors:
    print("Documentação canônica contém referências obsoletas:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)

print("OK: documentação canônica sem referências obsoletas")
