#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
C4_DIR="${C4_DIR:-$ROOT_DIR/docs/architecture/C4}"
PLANTUML_IMAGE="${PLANTUML_IMAGE:-plantuml/plantuml:1.2026.6}"

render() {
  local format="$1"
  docker run --rm \
    -v "$C4_DIR:/workspace" \
    -w /workspace \
    "$PLANTUML_IMAGE" \
    -charset UTF-8 "-$format" c4-context.puml c4-container.puml
}

render tsvg
render tpng
