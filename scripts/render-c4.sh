#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
C4_DIR="${C4_DIR:-$ROOT_DIR/docs/architecture/C4}"
PLANTUML_IMAGE="${PLANTUML_IMAGE:-plantuml/plantuml:1.2026.6}"

mapfile -t C4_SOURCES < <(
  find "$C4_DIR" -maxdepth 1 -type f -name '*.puml' -printf '%f\n' | sort
)

if [ "${#C4_SOURCES[@]}" -eq 0 ]; then
  echo "Nenhuma fonte C4 PlantUML encontrada em $C4_DIR." >&2
  exit 1
fi

render() {
  local format="$1"
  docker run --rm \
    -v "$C4_DIR:/workspace" \
    -w /workspace \
    "$PLANTUML_IMAGE" \
    -charset UTF-8 "-$format" "${C4_SOURCES[@]}"
}

render tsvg
render tpng

echo "Gerados SVG e PNG para ${#C4_SOURCES[@]} diagramas C4."
