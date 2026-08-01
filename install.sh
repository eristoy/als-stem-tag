#!/bin/sh
# Build als-stem-tag as a self-contained zipapp (single executable file).
#
# The tool is pure standard library, so the zipapp needs no venv and no pip
# install -- just Python 3.11+ on PATH. Re-run this after changing the source
# to refresh the installed copy.
#
# Usage: ./install.sh [destination]   (default: ~/.local/bin/als-stem-tag)
set -e

here=$(cd "$(dirname "$0")" && pwd)
dest="${1:-$HOME/.local/bin/als-stem-tag}"
interp="/usr/bin/env python3.14"

mkdir -p "$(dirname "$dest")"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT

cp -R "$here/src/als_stem_tag" "$stage/"
python3.14 -m zipapp "$stage" \
    --main "als_stem_tag.cli:main" \
    --python "$interp" \
    --output "$dest"
chmod +x "$dest"

echo "Installed $dest ($(du -h "$dest" | cut -f1))"
