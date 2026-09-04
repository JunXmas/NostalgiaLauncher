"""Danh mục phiên bản: phân tích, tra cứu, và chịu được dữ liệu lạ."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from mccore.errors import DataFileError, NetworkError
from mccore.model.json_value import JsonValue, as_list, as_mapping, as_string
from mccore.net.http import HttpClient
from mccore.repo.manifest import RELEASE, fetch_manifest, parse_manifest

FIXTURE = Path(__file__).resolve().parents[1] / "fixture" / "repo" / "version_manifest_v2.json"


def load_document() -> JsonValue:
    parsed: JsonValue = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return parsed


def test_parses_the_real_manifest_shape() -> None:
    manifest = parse_manifest(load_document())
    assert manifest.latest_release_id
    assert manifest.latest_snapshot_id
    assert len(manifest.entries_by_id) == 8


def test_lookup_is_by_identifier() -> None:
    manifest = parse_manifest(load_document())
    manifest_entry = manifest.find("1.20.1")
    assert manifest_entry is not None
    assert manifest_entry.release_type == RELEASE
    assert manifest_entry.remote.url.startswith("https://")
    assert manifest_entry.remote.sha1, (
        "danh mục công bố sha1 của từng file JSON — phải giữ để xác minh"
    )
    assert manifest.find("khong-co") is None


def test_released_filters_out_snapshots() -> None:
    manifest = parse_manifest(load_document())
    released = manifest.released()
    assert released
    assert all(manifest_entry.release_type == RELEASE for manifest_entry in released)
    assert len(released) < len(manifest.entries_by_id)


def test_order_from_the_server_is_kept() -> None:
    """Máy chủ xếp mới nhất trước; giao diện sau này sẽ dựa vào thứ tự đó."""
    document = load_document()
    ids_from_document = [
        as_string(as_mapping(manifest_entry).get("id"))
        for manifest_entry in as_list(as_mapping(document).get("versions"))
    ]
    manifest = parse_manifest(document)
    assert list(manifest.entries_by_id) == ids_from_document


def test_entries_missing_required_fields_are_skipped_not_fatal() -> None:
    """Một dòng hỏng không được làm hỏng cả danh mục 909 dòng."""
    document: JsonValue = {
        "latest": {"release": "a"},
        "versions": [
            {"id": "a", "url": "https://x/a.json", "type": "release"},
            {"id": "thieu-url", "type": "release"},
            {"url": "https://x/b.json", "type": "release"},
            "khong phai dict",
        ],
    }
    manifest = parse_manifest(document)
    assert list(manifest.entries_by_id) == ["a"]


def test_duplicate_identifiers_keep_the_first() -> None:
    document: JsonValue = {
        "versions": [
            {"id": "a", "url": "https://x/1.json"},
            {"id": "a", "url": "https://x/2.json"},
        ]
    }
    manifest = parse_manifest(document)
    manifest_entry = manifest.find("a")
    assert manifest_entry is not None
    assert manifest_entry.remote.url.endswith("1.json")


def test_fetch_rejects_a_body_that_is_not_json(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState
) -> None:
    server_state.add("/mc/game/version_manifest_v2.json", b"<html>loi</html>")
    with pytest.raises((DataFileError, NetworkError)):
        fetch_manifest(client, url=server.url("/mc/game/version_manifest_v2.json"))


def test_fetch_rejects_an_empty_manifest(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState
) -> None:
    """Danh mục rỗng nghĩa là máy chủ trả thứ không dùng được — hỏng ngay, đừng đi tiếp."""
    server_state.add("/mc/game/version_manifest_v2.json", b'{"versions": []}')
    with pytest.raises(DataFileError, match="rỗng"):
        fetch_manifest(client, url=server.url("/mc/game/version_manifest_v2.json"))
