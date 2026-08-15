#!/usr/bin/env bash
# Mở giao diện đồ hoạ Nostalgia Launcher.
#
# Qt6 cần libxcb-cursor.so.0, mà máy này chưa có gói libxcb-cursor0 và cài bằng
# apt thì phải có sudo. Bản sao thư viện để ở vendor/ (ngoài venv, để dựng lại
# venv không mất) và chỉ cần trỏ LD_LIBRARY_PATH vào đó. Muốn cài đàng hoàng:
#   sudo apt install libxcb-cursor0
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LD_LIBRARY_PATH="$here/vendor${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$here/.venv/bin/python" -m nostalgia gui "$@"
