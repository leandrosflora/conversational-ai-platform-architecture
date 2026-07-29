#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SEQUENCE_DIR="${SEQUENCE_DIR:-$ROOT_DIR/docs/architecture/sequence}"
PLANTUML_IMAGE="${PLANTUML_IMAGE:-plantuml/plantuml:1.2026.6}"

SEQUENCE_SOURCES=()
for source_path in "$SEQUENCE_DIR"/*.puml; do
  [ -e "$source_path" ] || continue
  SEQUENCE_SOURCES+=("${source_path##*/}")
done

if [ "${#SEQUENCE_SOURCES[@]}" -eq 0 ]; then
  echo "Nenhuma fonte de diagrama de sequência encontrada em $SEQUENCE_DIR." >&2
  exit 1
fi

render() {
  local format="$1"

  if [ -n "${PLANTUML_JAR:-}" ]; then
    (
      cd "$SEQUENCE_DIR"
      "${JAVA_BIN:-java}" -jar "$PLANTUML_JAR" -charset UTF-8 "-$format" "${SEQUENCE_SOURCES[@]}"
    )
    return
  fi

  docker run --rm \
    -v "$SEQUENCE_DIR:/workspace" \
    -w /workspace \
    "$PLANTUML_IMAGE" \
    -charset UTF-8 "-$format" "${SEQUENCE_SOURCES[@]}"
}

render tsvg
render tpng

echo "Gerados SVG e PNG para ${#SEQUENCE_SOURCES[@]} diagramas de sequência."
