#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$ROOT_DIR/docs/architecture/sequence"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cp -a "$SOURCE_DIR/." "$TMP_DIR/"
SEQUENCE_DIR="$TMP_DIR" "$ROOT_DIR/scripts/render-sequence-diagrams.sh"

SEQUENCE_SOURCES=()
for source_path in "$SOURCE_DIR"/*.puml; do
  [ -e "$source_path" ] || continue
  SEQUENCE_SOURCES+=("${source_path##*/}")
done

if [ "${#SEQUENCE_SOURCES[@]}" -eq 0 ]; then
  echo "Nenhuma fonte de diagrama de sequência encontrada em $SOURCE_DIR." >&2
  exit 1
fi

for source in "${SEQUENCE_SOURCES[@]}"; do
  base="${source%.puml}"
  for extension in svg png; do
    file="$base.$extension"
    if [ ! -f "$SOURCE_DIR/$file" ]; then
      echo "Artefato ausente: docs/architecture/sequence/$file" >&2
      echo "Execute scripts/render-sequence-diagrams.sh e versione os artefatos gerados." >&2
      exit 1
    fi
    if ! cmp -s "$SOURCE_DIR/$file" "$TMP_DIR/$file"; then
      echo "Diagrama desatualizado: docs/architecture/sequence/$file" >&2
      echo "Execute scripts/render-sequence-diagrams.sh e versione os artefatos gerados." >&2
      exit 1
    fi
  done
done

echo "SVG e PNG de todos os diagramas de sequência estão sincronizados com as fontes PlantUML."
