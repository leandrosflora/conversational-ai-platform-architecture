#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$ROOT_DIR/docs/architecture/C4"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cp -a "$SOURCE_DIR/." "$TMP_DIR/"
C4_DIR="$TMP_DIR" "$ROOT_DIR/scripts/render-c4.sh"

for file in c4-context.svg c4-context.png c4-container.svg c4-container.png; do
  if ! cmp -s "$SOURCE_DIR/$file" "$TMP_DIR/$file"; then
    echo "Diagrama desatualizado: docs/architecture/C4/$file" >&2
    echo "Execute scripts/render-c4.sh e versione os artefatos gerados." >&2
    exit 1
  fi
done

echo "Diagramas C4 sincronizados com as fontes PlantUML."
