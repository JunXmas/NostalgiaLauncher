"""Bundled UI labels for native controls outside QML."""

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=2)
def load_translations(language: str) -> dict[str, str]:
    language = "en" if language == "en" else "vi"
    path = Path(__file__).parent / "qml" / "i18n" / f"{language}.json"
    return dict(json.loads(path.read_text(encoding="utf-8")))


def phrase(source: str, language: str) -> str:
    return load_translations(language).get("p:" + source, source)
