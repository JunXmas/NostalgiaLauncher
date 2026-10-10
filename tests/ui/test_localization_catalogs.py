"""Catalog completeness and placeholder contracts for both shipped languages."""

import json
import re

from nostalgia.ui.app import QML_DIR
from nostalgia.ui.translations import load_translations


def test_catalogs_cover_ui_and_guides_with_matching_placeholders() -> None:
    english, vietnamese = load_translations("en"), load_translations("vi")
    assert english.keys() == vietnamese.keys()
    for key in english:
        assert english[key] and vietnamese[key], key
        placeholder_pattern = r"\{\d+\}|%[1-9]\d*"
        assert sorted(re.findall(placeholder_pattern, english[key])) == sorted(
            re.findall(placeholder_pattern, vietnamese[key])
        ), key
    missing = []
    for path in QML_DIR.rglob("*.qml"):
        source = path.read_text(encoding="utf-8")
        for match in re.finditer(r'Tr\.(?:phrase|format|plural)\(("(?:\\.|[^"\\])*")', source):
            phrase = json.loads(match[1])
            if "p:" + phrase not in english:
                missing.append(f"{path.name}: {phrase}")
    guides = QML_DIR / "preview" / "GuideCatalog.js"
    for literal in re.findall(r'"(?:\\.|[^"\\])*"', guides.read_text(encoding="utf-8")):
        phrase = json.loads(literal)
        if any(ord(char) > 127 and char.isalpha() for char in phrase):
            assert "p:" + phrase in english, phrase
    assert not missing, missing


def test_no_duplicate_catalog_keys() -> None:
    def unique_fields(pairs: list[tuple[str, str]]) -> dict[str, str]:
        assert len(pairs) == len(dict(pairs))
        return dict(pairs)

    for language in ("en", "vi"):
        path = QML_DIR / "i18n" / f"{language}.json"
        json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_fields)
