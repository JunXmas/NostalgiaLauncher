"""Manifest và chỉ mục riêng, ghim theo research lock của build đã kiểm chữ ký."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from nostalgia.errors import IntegrityError
from nostalgia.horizon.model import HorizonBuild
from nostalgia.install.assets import plan_asset_index_task
from nostalgia.model.download import DownloadTask
from nostalgia.model.json_value import as_mapping, as_string
from nostalgia.net.download import download_one
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.files import ensure_dir, read_json, sha1_of_file
from nostalgia.storage.paths import DataPaths
from nostalgia.version.meta import VersionMeta, parse_version_meta


@dataclass(frozen=True, slots=True)
class HorizonInputs:
    paths: DataPaths
    version_meta: VersionMeta


def sync_horizon_inputs(
    http_client: HttpClient,
    paths: DataPaths,
    build: HorizonBuild,
    cancel_token: CancelToken | None = None,
) -> HorizonInputs:
    lock = as_mapping(
        as_mapping(read_json(build.build_dir / "research-lock.json")).get("minecraft")
    )
    sha1 = as_string(lock.get("manifest_sha1")) or ""
    if (
        lock.get("version") != build.game_version
        or lock.get("java_major") != build.java_major
        or re.fullmatch(r"[0-9a-f]{40}", sha1) is None
        or any(
            re.fullmatch(r"[0-9a-f]{40}", as_string(lock.get(f"{side}_sha1")) or "") is None
            for side in ("client", "server")
        )
    ):
        raise IntegrityError("Horizon research lock has no valid pinned Minecraft manifest")
    input_paths = DataPaths(
        build.build_dir.parent / "inputs", build.build_dir.parent / "input-config"
    )
    task = DownloadTask(
        f"https://piston-meta.mojang.com/v1/packages/{sha1}/{build.game_version}.json",
        input_paths.version_json(build.game_version),
        sha1,
    )
    write_cached_input(task, paths.version_json(build.game_version), cancel_token=cancel_token)
    download_one(http_client, task, cancel_token=cancel_token)
    document = as_mapping(read_json(task.destination))
    downloads = as_mapping(document.get("downloads"))
    if document.get("id") != build.game_version or any(
        as_mapping(downloads.get(side)).get("sha1") != lock.get(f"{side}_sha1")
        for side in ("client", "server")
    ):
        raise IntegrityError("Pinned Minecraft manifest does not match the Horizon jars")
    version_meta = parse_version_meta(document)
    if version_meta.asset_index is None:
        raise IntegrityError("Pinned Horizon manifest has no asset index")
    task = plan_asset_index_task(version_meta.asset_index, input_paths)
    write_cached_input(
        task,
        paths.asset_index_json(version_meta.asset_index.asset_index_id),
        cancel_token=cancel_token,
    )
    download_one(http_client, task, cancel_token=cancel_token)
    return HorizonInputs(input_paths, version_meta)


def write_cached_input(
    task: DownloadTask,
    source: Path,
    *,
    link_object: bool = False,
    cancel_token: CancelToken | None = None,
) -> None:
    """Chỉ ghi kho đầu vào riêng; metadata luôn chép, object bất biến có thể liên kết cứng."""
    if cancel_token is not None:
        cancel_token.raise_if_cancelled()
    if not task.sha1:
        raise IntegrityError("Horizon input has no checksum")
    if task.destination.is_file():
        if sha1_of_file(task.destination) == task.sha1:
            return
        task.destination.unlink()
    if source.is_file() and not source.is_symlink() and sha1_of_file(source) == task.sha1:
        ensure_dir(task.destination.parent)
        if link_object:
            try:
                os.link(source, task.destination)
                return
            except OSError:
                pass
        shutil.copyfile(source, task.destination)
