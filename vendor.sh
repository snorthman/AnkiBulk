#!/usr/bin/env bash
# vendor.sh - repopulates AnkiBulk/internal with packages
# Anki 25.09 doesn't already bundle.
set -euo pipefail

VENDOR="AnkiBulk/internal"
rm -rf "$VENDOR"
mkdir -p "$VENDOR"

pip install --target "$VENDOR" --no-deps \
    "PyYAML==6.0.2"

# Drop installer metadata and shims - not needed at runtime.
rm -rf "$VENDOR"/*.dist-info "$VENDOR"/bin "$VENDOR"/Scripts
find "$VENDOR" -type d -name __pycache__ -exec rm -rf {} +

# PyYAML: remove C extension (libyaml) - pure-Python fallback is sufficient.
rm -rf "$VENDOR/_yaml" "$VENDOR"/yaml/*.pyd "$VENDOR"/yaml/*.so

read -n 1 -s
