"""Cài đầu vào Horizon theo manifest ghim, dùng lại thư viện và Java của kho chung."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nostalgia.errors import InstanceError
from nostalgia.horizon.input import sync_horizon_inputs, write_cached_input
from nostalgia.horizon.model import HorizonBuild
from nostalgia.horizon.resource import sync_server_jar
from nostalgia.install.assets import load_installed_asset_index, plan_asset_tasks
from nostalgia.install.client import plan_client_task
from nostalgia.install.library import plan_libraries
from nostalgia.java.mojang_jre import ensure_java_runtime
from nostalgia.net.download import download_all
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.repo.endpoints import DEFAULT_ENDPOINTS, Endpoints
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform


@dataclass(frozen=True, slots=True)
class HorizonPreparation:
    input_paths: DataPaths
    java_binary: Path
    server_jar: Path


def sync_horizon_preparation(
    http_client: HttpClient,
    paths: DataPaths,
    build: HorizonBuild,
    platform: Platform,
    *,
    on_progress: ProgressFn = ignore_progress,
    cancel_token: CancelToken | None = None,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
) -> HorizonPreparation:
    inputs = sync_horizon_inputs(http_client, paths, build, cancel_token)
    tasks = list(plan_libraries(inputs.version_meta, platform, paths).downloads)
    client_task = plan_client_task(inputs.version_meta, paths)
    if client_task is not None:
        tasks.append(client_task)
    asset_index = load_installed_asset_index(inputs.version_meta, inputs.paths)
    if asset_index is None:
        raise InstanceError("Horizon pinned asset index is missing")
    for task in plan_asset_tasks(asset_index, inputs.paths, base_url=endpoints.asset_objects):
        write_cached_input(
            task,
            paths.asset_objects_dir / task.destination.parent.name / task.destination.name,
            link_object=True,
            cancel_token=cancel_token,
        )
        tasks.append(task)
    report = download_all(http_client, tasks, on_progress=on_progress, cancel_token=cancel_token)
    if not report.ok:
        raise InstanceError(f"Cannot prepare Horizon inputs: {report.failures[0].reason}")
    installed_runtime = ensure_java_runtime(
        http_client,
        paths,
        inputs.version_meta,
        platform,
        on_progress=on_progress,
        cancel_token=cancel_token,
        catalog_url=endpoints.java_catalog,
    )
    server_jar = sync_server_jar(http_client, paths, build, inputs.paths, cancel_token)
    return HorizonPreparation(inputs.paths, installed_runtime.java_binary, server_jar)
