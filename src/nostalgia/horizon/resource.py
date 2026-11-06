"""Chuẩn bị tài nguyên từ kho Minecraft riêng, không chạm vào thế giới người chơi."""

from __future__ import annotations

from pathlib import Path

from nostalgia.errors import InstanceError
from nostalgia.horizon.command import HorizonCommand
from nostalgia.horizon.model import HorizonBuild
from nostalgia.horizon.process import run_horizon_task
from nostalgia.model.download import DownloadTask
from nostalgia.model.json_value import as_integer, as_mapping, as_string
from nostalgia.net.download import download_one
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.storage.files import read_json
from nostalgia.storage.paths import DataPaths


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
) -> Path:
    fields = as_mapping(read_json(paths.version_json(build.game_version)))
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
        str(paths.version_json(build.game_version)),
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
