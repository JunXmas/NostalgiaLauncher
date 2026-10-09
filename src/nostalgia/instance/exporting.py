"""Xuất ZIP CurseForge hoặc MRPACK Modrinth tự chứa nội dung, ghi file nguyên tử."""

from __future__ import annotations

import json
import os
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from nostalgia.errors import InstanceError
from nostalgia.instance.export_payload import ExportFile, list_export_files
from nostalgia.instance.model import Instance
from nostalgia.modloader.model import LoaderKind


@dataclass(frozen=True, slots=True)
class ExportEnvironment:
    game_version: str
    loader_kind: LoaderKind
    loader_version: str


@dataclass(frozen=True, slots=True)
class ModpackExport:
    path: Path
    display_name: str
    archive_format: str
    file_count: int
    size_bytes: int


def export_modpack(
    instance: Instance,
    game_dir: Path,
    environment: ExportEnvironment,
    destination: Path,
    archive_format: str,
    *,
    include_worlds: bool = False,
    overwrite: bool = False,
) -> ModpackExport:
    if archive_format not in ("mrpack", "zip"):
        raise InstanceError("chọn định dạng MRPACK hoặc ZIP")
    if destination.suffix.lower() != "." + archive_format:
        raise InstanceError("đuôi file không khớp định dạng modpack đã chọn")
    if not environment.game_version or environment.game_version in ("latest", "latest-release"):
        raise InstanceError("chưa xác định được phiên bản Minecraft để xuất modpack")
    if environment.loader_kind != "vanilla" and not environment.loader_version:
        raise InstanceError("chưa xác định được phiên bản loader để xuất modpack")
    if destination.is_symlink() or destination.resolve().is_relative_to(game_dir.resolve()):
        raise InstanceError("hãy lưu modpack bên ngoài thư mục bản chơi")
    if destination.exists() and not overwrite:
        raise InstanceError("file xuất đã tồn tại; hãy chọn tên khác")
    files = list_export_files(game_dir, include_worlds=include_worlds)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".modpack-", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            _write_manifest(archive, instance, environment, archive_format)
            for exported_file in files:
                _write_payload(archive, exported_file)
        if files != list_export_files(game_dir, include_worlds=include_worlds):
            raise InstanceError("dữ liệu bản chơi vừa thay đổi; hãy xuất lại khi game đã dừng")
        if not overwrite and destination.exists():
            raise InstanceError("file xuất đã tồn tại; hãy chọn tên khác")
        temporary.replace(destination)
    except (OSError, zipfile.BadZipFile) as error:
        raise InstanceError(f"không xuất được modpack: {error}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return ModpackExport(
        destination, instance.label, archive_format, len(files), destination.stat().st_size
    )


def _write_manifest(
    archive: zipfile.ZipFile,
    instance: Instance,
    environment: ExportEnvironment,
    archive_format: str,
) -> None:
    if archive_format == "mrpack":
        dependencies = {"minecraft": environment.game_version}
        if environment.loader_kind != "vanilla":
            dependency_key = {
                "fabric": "fabric-loader",
                "quilt": "quilt-loader",
                "forge": "forge",
                "neoforge": "neoforge",
            }[environment.loader_kind]
            dependencies[dependency_key] = environment.loader_version
        archive.writestr(
            "modrinth.index.json",
            json.dumps(
                {
                    "formatVersion": 1,
                    "game": "minecraft",
                    "versionId": "1.0.0",
                    "name": instance.label,
                    "summary": "Exported from Nostalgia Launcher",
                    "files": [],
                    "dependencies": dependencies,
                },
                ensure_ascii=False,
            ),
        )
    else:
        mod_loaders = (
            []
            if environment.loader_kind == "vanilla"
            else [
                {
                    "id": environment.loader_kind + "-" + environment.loader_version,
                    "primary": True,
                }
            ]
        )
        archive.writestr(
            "manifest.json",
            json.dumps(
                {
                    "manifestType": "minecraftModpack",
                    "manifestVersion": 1,
                    "name": instance.label,
                    "version": "1.0.0",
                    "author": "",
                    "minecraft": {"version": environment.game_version, "modLoaders": mod_loaders},
                    "files": [],
                    "overrides": "overrides",
                },
                ensure_ascii=False,
            ),
        )


def _write_payload(archive: zipfile.ZipFile, exported_file: ExportFile) -> None:
    if exported_file.path.is_symlink():
        raise InstanceError("dữ liệu bản chơi vừa đổi thành liên kết; đã dừng xuất")
    written = 0
    with (
        exported_file.path.open("rb") as source,
        archive.open("overrides/" + exported_file.relative_path, "w", force_zip64=True) as target,
    ):
        while block := source.read(1024 * 1024):
            written += len(block)
            if written > exported_file.size_bytes:
                raise InstanceError("file modpack vừa thay đổi; hãy xuất lại")
            target.write(block)
    if written != exported_file.size_bytes:
        raise InstanceError("file modpack vừa thay đổi; hãy xuất lại")
