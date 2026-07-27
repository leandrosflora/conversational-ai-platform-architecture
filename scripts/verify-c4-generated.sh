#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$ROOT_DIR/docs/architecture/C4"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cp -a "$SOURCE_DIR/." "$TMP_DIR/"
C4_DIR="$TMP_DIR" "$ROOT_DIR/scripts/render-c4.sh"

mapfile -t C4_SOURCES < <(
  find "$SOURCE_DIR" -maxdepth 1 -type f -name '*.puml' -printf '%f\n' | sort
)

if [ "${#C4_SOURCES[@]}" -eq 0 ]; then
  echo "Nenhuma fonte C4 PlantUML encontrada em $SOURCE_DIR." >&2
  exit 1
fi

for source in "${C4_SOURCES[@]}"; do
  base="${source%.puml}"
  for extension in svg png; do
    file="$base.$extension"
    if [ ! -f "$SOURCE_DIR/$file" ]; then
      echo "Artefato ausente: docs/architecture/C4/$file" >&2
      echo "Execute scripts/render-c4.sh e versione os artefatos gerados." >&2
      exit 1
    fi
    if ! cmp -s "$SOURCE_DIR/$file" "$TMP_DIR/$file"; then
      echo "Diagrama desatualizado: docs/architecture/C4/$file" >&2
      echo "Execute scripts/render-c4.sh e versione os artefatos gerados." >&2
      exit 1
    fi
  done
done

echo "SVG e PNG de todos os diagramas C4 estão sincronizados com as fontes PlantUML."
