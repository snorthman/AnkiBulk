#!/usr/bin/env bash
# vendor.sh - repopulates AnkiSensei/internal with packages
# Anki 25.09 doesn't already bundle.
set -euo pipefail

VENDOR="AnkiBulk/internal"
rm -rf "$VENDOR"
mkdir -p "$VENDOR"

pip install --target "$VENDOR" --no-deps \
    "fluent.runtime==0.4.0" \
    "fluent.syntax==0.19.0" \
    "PyYAML==6.0.2"

# Fluent: Drop installer metadata and shims - not needed at runtime.
rm -rf "$VENDOR"/*.dist-info "$VENDOR"/bin "$VENDOR"/Scripts
find "$VENDOR" -type d -name __pycache__ -exec rm -rf {} +

# PyYAML: remove C extension (libyaml) - pure-Python fallback is sufficient.
rm -rf "$VENDOR/_yaml" "$VENDOR"/yaml/*.pyd "$VENDOR"/yaml/*.so

echo "Done. Press any key to continue..."
read -n 1 -s