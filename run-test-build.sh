#!/usr/bin/env bash
# Chạy bản gộp skin-Ely + cape-Microsoft trong HOME RIÊNG.
# Config thật ở ~/.config/nostalgia KHÔNG bị đụng tới.
set -euo pipefail
cd "$(dirname "$0")"
REAL_HOME=$HOME
export HOME=/tmp/nostalgia-test-home
export XDG_CONFIG_HOME=$HOME/.config
export XDG_DATA_HOME=$HOME/.local/share
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME"
exec ./.venv/bin/python -c 'from nostalgia.ui.app import main; main()' "$@"
