"""Bản mới cho mod đã cài, và nhận diện file chép tay bằng sha1 — logic thuần, không mạng."""

from __future__ import annotations

import hashlib
from pathlib import Path

from nostalgia.content.installed import LedgerEntry, list_installed, load_ledger, save_ledger
from nostalgia.content.model import Project, ProjectVersion
from nostalgia.content.updates import find_updates, identify_by_hash


def make_version(version_id: str, project_id: str, version_type: str = "release") -> ProjectVersion:
    return ProjectVersion(
        version_id=version_id,
        project_id=project_id,
        version_number=version_id,
        version_type=version_type,
        game_versions=("1.20.1",),
        loaders=("fabric",),
        date_published="",
        file_url="u",
        file_name=f"{project_id}-{version_id}.jar",
        file_sha1="0" * 40,
        file_size=1,
        required_project_ids=(),
    )


def seed(game_dir: Path) -> Path:
    mods = game_dir / "mods"
    mods.mkdir(parents=True)
    (mods / "sodium-v1.jar").write_bytes(b"cu")
    (mods / "la.jar").write_bytes(b"chep tay")
    save_ledger(mods, {"S": LedgerEntry("S", "Sodium", "v1", "v1", "sodium-v1.jar")})
    return mods


def test_updates_only_for_known_files_with_a_newer_compatible_release(tmp_path: Path) -> None:
    seed(tmp_path)
    calls: list[tuple[str, str]] = []

    def fetch(source: str, project_id: str) -> tuple[ProjectVersion, ...]:
        calls.append((source, project_id))
        return (make_version("v3", "S", "beta"), make_version("v2", "S"), make_version("v1", "S"))

    updates = find_updates(
        list_installed(tmp_path, "mod"),
        fetch,
        game_version="1.20.1",
        loader_kind="fabric",
        content_kind="mod",
    )

    assert calls == [("modrinth", "S")], "file chép tay không có dự án thì không hỏi"
    assert [(u.installed.file_name, u.latest.version_id) for u in updates] == [
        ("sodium-v1.jar", "v2")
    ]


def test_no_update_when_already_on_the_latest_compatible(tmp_path: Path) -> None:
    seed(tmp_path)
    updates = find_updates(
        list_installed(tmp_path, "mod"),
        lambda _s, p: (make_version("v1", p),),
        game_version="1.20.1",
        loader_kind="fabric",
        content_kind="mod",
    )
    assert updates == ()


def test_identify_hashes_unknown_files_and_writes_the_ledger(tmp_path: Path) -> None:
    mods = seed(tmp_path)
    sha1 = hashlib.sha1(b"chep tay").hexdigest()
    seen: list[tuple[str, ...]] = []

    def lookup(hashes: tuple[str, ...]) -> dict[str, ProjectVersion]:
        seen.append(hashes)
        return {sha1: make_version("v9", "L")}

    def describe(_ids: tuple[str, ...]) -> dict[str, Project]:
        return {
            "L": Project(
                project_id="L",
                project_slug="la",
                title="Lạ mà quen",
                description="",
                author="",
                content_kind="mod",
                icon_url="https://x/la.png",
                downloads=0,
                follows=0,
                loaders=("fabric",),
            )
        }

    found = identify_by_hash(tmp_path, "mod", list_installed(tmp_path, "mod"), lookup, describe)

    assert found == 1
    assert seen == [(sha1,)], "chỉ băm file chưa có trong sổ"
    ledger_entry = load_ledger(mods)["L"]
    assert (
        ledger_entry.title,
        ledger_entry.file_name,
        ledger_entry.icon_url,
        ledger_entry.version_id,
    ) == (
        "Lạ mà quen",
        "la.jar",
        "https://x/la.png",
        "v9",
    )
    assert identify_by_hash(tmp_path, "mod", list_installed(tmp_path, "mod"), lookup, describe) == 0
