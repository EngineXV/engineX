#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
VERSION="$(python3 -c 'import json, pathlib; print(json.loads(pathlib.Path("'"$ROOT"'/manifest.json").read_text())["version"])')"

mkdir -p "$DIST"
ZIP="$DIST/engine-browser-bridge-${VERSION}.zip"
rm -f "$ZIP"
(
  cd "$ROOT"
  zip -r "$ZIP" manifest.json background.js popup.html popup.js README.md -x "dist/*" "scripts/*"
)

echo "Built $ZIP"
