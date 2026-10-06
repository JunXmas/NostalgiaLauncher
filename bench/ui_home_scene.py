"""Xuất PNG góc Minecraft ở Home từ các model vanilla đóng kèm, không dựng lại model.

.venv/bin/python bench/ui_home_scene.py --output /tmp/home-island.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from nostalgia.ui.home_scene import render_home_scene


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not render_home_scene().save(str(args.output)):
        parser.error("Không ghi được ảnh góc Minecraft")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
