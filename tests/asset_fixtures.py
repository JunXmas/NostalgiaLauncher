"""Nạp chỉ mục asset cắt từ bản THẬT của Mojang."""

from __future__ import annotations

import json
from pathlib import Path

from nostalgia.model.json_value import JsonValue

FIXTURE_DIRECTORY = Path(__file__).resolve().parent / "fixture" / "assets"


def load_asset_index(asset_index_id: str) -> JsonValue:
    """`5` là 1.20.1, `legacy` là 1.6.4 (virtual), `pre-1.6` là 1.5.2 (map_to_resources)."""
    parsed: JsonValue = json.loads(
        (FIXTURE_DIRECTORY / f"{asset_index_id}.json").read_text(encoding="utf-8")
    )
    return parsed
