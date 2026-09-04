"""Nạp fixture manifest bản Java — cắt từ manifest thật của Mojang, giữ nguyên cấu trúc.

Bản cắt giữ lại đúng những hình dạng dễ sai: khoá hệ điều hành có component nhưng **danh
sách rỗng** (`mac-os-arm64` không phát hành `jre-legacy`), file có và không có bản nén lzma,
file có cờ thực thi, và cả ba liên kết tượng trưng — trong đó một cái trỏ ngược qua `..`.
"""

from __future__ import annotations

import json
from pathlib import Path

from mccore.model.json_value import JsonValue

FIXTURE_DIRECTORY = Path(__file__).resolve().parent / "fixture" / "java"


def load_catalog_document() -> JsonValue:
    parsed: JsonValue = json.loads((FIXTURE_DIRECTORY / "all.json").read_text(encoding="utf-8"))
    return parsed


def load_layout_document() -> JsonValue:
    path = FIXTURE_DIRECTORY / "jre-legacy-linux.json"
    parsed: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    return parsed
