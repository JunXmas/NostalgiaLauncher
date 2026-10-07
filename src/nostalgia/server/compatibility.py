"""Folia requires an explicit root plugin descriptor flag, not just a Paper category."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path


def folia_supported(path: Path) -> bool:
    with zipfile.ZipFile(path) as archive:
        for file_name in ("plugin.yml", "paper-plugin.yml"):
            if file_name not in archive.namelist():
                continue
            info = archive.getinfo(file_name)
            if info.file_size > 128_000:
                return False
            text = archive.read(file_name).decode("utf-8", errors="replace")
            if re.search(r"(?m)^folia-supported\s*:\s*true\s*(?:#.*)?$", text):
                return True
    return False
