"""Chuẩn bị tài nguyên từ kho Minecraft riêng, không chạm vào thế giới người chơi."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path

from nostalgia.errors import InstanceError, IntegrityError
from nostalgia.horizon.command import HorizonCommand
from nostalgia.horizon.model import HorizonBuild
from nostalgia.horizon.process import run_horizon_task
from nostalgia.model.download import DownloadTask
from nostalgia.model.json_value import as_integer, as_mapping, as_string
from nostalgia.net.download import download_one
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.storage.files import read_json, sha1_of_file, sync_directory
from nostalgia.storage.paths import DataPaths



def sync_horizon_manifest(
    http_client: HttpClient,
    build: HorizonBuild,
    cancel_token: CancelToken | None = None,
) -> Path:
    """Dùng manifest Mojang gốc mà Horizon đã ghim, không sửa cache Java dùng chung.

    Mojang có thể phát hành lại version JSON 26.3 với asset index khác. Metadata
    trong versions/26.3/26.3.json vẫn hợp lệ cho Java nhưng Horizon xác minh
    SHA-1 theo research-lock của chính binary native.
    """
    lock = as_mapping(read_json(build.build_dir / "research-lock.json"))
    minecraft = as_mapping(lock.get("minecraft"))
    version = as_string(minecraft.get("version"))
    expected_sha1 = as_string(minecraft.get("manifest_sha1")) or ""
    if version != build.game_version or re.fullmatch(r"[0-9a-f]{40}", expected_sha1) is None:
        raise InstanceError("Horizon build has no valid pinned Minecraft version manifest")

    destination = build.build_dir.parent / "minecraft" / version / "manifest.json"
    if destination.is_file() and sha1_of_file(destination) == expected_sha1:
        return destination

    url = f"https://piston-meta.mojang.com/v1/packages/{expected_sha1}/{version}.json"
    payload = http_client.fetch_bytes(url, max_bytes=1024 * 1024, cancel_token=cancel_token)
    if hashlib.sha1(payload).hexdigest() != expected_sha1:
        raise IntegrityError("Mojang Horizon version manifest SHA-1 mismatch")

    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".manifest.", dir=destination.parent)
    staged = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        staged.replace(destination)
        sync_directory(destination.parent)
    finally:
        staged.unlink(missing_ok=True)
    return destination

def check_resources(build: HorizonBuild, cancel_token: CancelToken | None = None) -> bool:
    report = run_horizon_task(
        HorizonCommand(
            (str(build.prepare_binary), "--check", "--output", str(build.resources_dir)),
            build.build_dir.parent,
        ),
        cancel_token=cancel_token,
        timeout_seconds=60,
    )
    return report.exit_code == 0


def sync_server_jar(
    http_client: HttpClient,
    paths: DataPaths,
    build: HorizonBuild,
    cancel_token: CancelToken | None = None,
    *,
    version_json: Path | None = None,
) -> Path:
    fields = as_mapping(read_json(version_json or paths.version_json(build.game_version)))
    server_fields = as_mapping(as_mapping(fields.get("downloads")).get("server"))
    url = as_string(server_fields.get("url")) or ""
    sha1 = as_string(server_fields.get("sha1")) or ""
    size = as_integer(server_fields.get("size"))
    if not url.startswith("https://") or len(sha1) != 40 or size is None or size <= 0:
        raise InstanceError("Minecraft version metadata has no verified server jar for Horizon")
    server_jar = paths.data_dir / "horizon" / "game" / build.game_version / "server.jar"
    download_one(http_client, DownloadTask(url, server_jar, sha1, size), cancel_token=cancel_token)
    return server_jar


def prepare_resources(
    paths: DataPaths,
    build: HorizonBuild,
    java_binary: Path,
    server_jar: Path,
    *,
    version_json: Path,
    on_progress: ProgressFn = ignore_progress,
    cancel_token: CancelToken | None = None,
) -> None:
    argv = [
        str(build.prepare_binary),
        "--prepare",
        "--complete",
        "--progress",
        "json",
        "--output",
        str(build.resources_dir),
        "--root",
        str(build.build_dir),
        "--version-json",
        str(version_json),
        "--client-jar",
        str(paths.version_jar(build.game_version)),
        "--libraries-dir",
        str(paths.libraries_dir),
        "--assets-dir",
        str(paths.assets_dir),
        "--server-jar",
        str(server_jar),
        "--java-home",
        str(java_binary.parent.parent),
    ]
    report = run_horizon_task(
        HorizonCommand(tuple(argv), build.build_dir.parent),
        cancel_token=cancel_token,
        on_progress=on_progress,
    )
    if report.exit_code or not check_resources(build, cancel_token):
        raise InstanceError(
            "Horizon resources are incomplete; retry preparation\n" + "\n".join(report.tail)
        )
