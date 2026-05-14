#!/usr/bin/env bash
# Package AnkiBulk as a .ankiaddon file for distribution.
#
# Usage:  ./package.sh
# Output: AnkiBulk.ankiaddon (in the repo root)

set -euo pipefail
cd "$(dirname "$0")"

OUT="AnkiBulk.ankiaddon"

# Clean __pycache__ directories
find AnkiBulk -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Build the zip — contents at the root, no top-level folder
rm -f "$OUT"
cd AnkiBulk
zip -r "../$OUT" . \
    -x "./__pycache__/*" \
    -x "./**/__pycache__/*"
cd ..

echo "Packaged: $OUT ($(du -h "$OUT" | cut -f1))"
