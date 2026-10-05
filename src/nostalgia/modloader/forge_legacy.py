"""Forge đời cũ (≤ 1.12.1): installer chỉ có giao diện, không có `--installClient`.

Làm đúng việc giao diện đó làm, nhưng không cần chạy Java: `install_profile.json` đã chứa
nguyên một version JSON (`versionInfo`, có `inheritsFrom`) và jar universal nằm ngay trong
installer. Ghi JSON vào kho version, đặt jar universal vào `libraries/` theo toạ độ maven —
phần thư viện còn lại khai kiểu maven (`name` + `url`) mà parser đã hiểu, nên
`install_version(version_id)` tải nốt và launch đi đường quen (launchwrapper).
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from nostalgia.errors import VersionError
from nostalgia.model.json_value import JsonValue, as_list, as_mapping, as_string
from nostalgia.storage.files import atomic_write_json, ensure_dir, resolve_within
from nostalgia.version.maven import MavenCoordinate

PROFILE_MEMBER = "install_profile.json"


def is_legacy_installer(jar_path: Path) -> bool:
    """Installer cũ có `versionInfo` ngay trong install_profile.json; installer mới thì không."""
    try:
        with zipfile.ZipFile(jar_path) as archive:
            install_profile = json.loads(archive.read(PROFILE_MEMBER))
    except (KeyError, OSError, zipfile.BadZipFile, ValueError):
        return False
    return isinstance(install_profile, dict) and "versionInfo" in install_profile


def install_legacy_forge(jar_path: Path, versions_dir: Path, libraries_dir: Path) -> str:
    """Ghi version JSON và jar universal từ installer cũ; trả về `version_id`. Không chạm mạng."""
    with zipfile.ZipFile(jar_path) as archive:
        install_profile: JsonValue = json.loads(archive.read(PROFILE_MEMBER))
        fields = as_mapping(install_profile)
        install = as_mapping(fields.get("install"))
        version_info = as_mapping(fields.get("versionInfo"))
        version_id = as_string(version_info.get("id"))
        coordinate_text = as_string(install.get("path"))
        universal_member = as_string(install.get("filePath"))
        if not version_id or not coordinate_text or not universal_member:
            message = (
                "install_profile.json của Forge cũ thiếu versionInfo.id / install.path / filePath"
            )
            raise VersionError(message)
        try:
            universal = archive.read(universal_member)
        except KeyError as exc:
            message = f"installer Forge cũ không có jar universal {universal_member!r}"
            raise VersionError(message) from exc

    # Thư viện chỉ dành cho server (clientreq: false) bị bỏ, để classpath client không kể tới
    # jar mà ta cố tình không tải.
    libraries = [
        raw
        for raw in as_list(version_info.get("libraries"))
        if as_mapping(raw).get("clientreq") is not False
    ]
    document: dict[str, JsonValue] = {**version_info, "libraries": libraries}
    version_dir = ensure_dir(resolve_within(versions_dir, version_id))
    atomic_write_json(version_dir / f"{version_id}.json", document)

    # Jar universal đặt đúng chỗ toạ độ maven trỏ tới (bỏ hậu tố -universal, như installer làm).
    destination = resolve_within(
        libraries_dir, MavenCoordinate.parse(coordinate_text).relative_path
    )
    ensure_dir(destination.parent)
    destination.write_bytes(universal)
    return version_id
