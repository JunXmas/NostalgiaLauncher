"""Đọc Launch API từ đúng bản dựng trước khi chuẩn bị hoặc chạy game."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from nostalgia.errors import InstanceError
from nostalgia.horizon.environment import build_horizon_environment
from nostalgia.horizon.model import HORIZON_GAME_VERSION, HorizonBuild
from nostalgia.model.json_value import JsonValue, as_integer, as_list, as_mapping, as_string
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform, resolve_creation_flags


def load_build(paths: DataPaths, build_id: str, platform: Platform) -> HorizonBuild:
    from nostalgia.horizon.model import resolve_build_dir

    build_dir = resolve_build_dir(paths, build_id)
    suffix = ".exe" if platform.os_name == "windows" else ""
    executable = build_dir / ("horizon-prepare" + suffix)
    prepare_fields = _load_api(executable, build_dir)
    game_fields = _load_api(build_dir / ("horizon-client" + suffix), build_dir)
    version_id = as_string(prepare_fields.get("minecraft")) or ""
    java_major = as_integer(prepare_fields.get("java_major")) or 0
    if version_id != HORIZON_GAME_VERSION or game_fields.get("minecraft") != version_id:
        raise InstanceError("This Horizon build requires a different Minecraft version")
    if java_major != 25:
        raise InstanceError("Unsupported Horizon preparation Java version")
    _require_options(game_fields, {"--resources", "--game-dir", "--home", "--session-stdin"})
    _require_options(
        prepare_fields,
        {
            "--prepare",
            "--check",
            "--complete",
            "--output",
            "--version-json",
            "--client-jar",
            "--libraries-dir",
            "--assets-dir",
            "--server-jar",
            "--java-home",
            "--progress",
        },
    )
    return HorizonBuild(build_id, build_dir, version_id, java_major, suffix)


def _load_api(executable: Path, build_dir: Path) -> dict[str, JsonValue]:
    try:
        response = subprocess.run(
            [str(executable), "--launch-api"],
            cwd=build_dir,
            capture_output=True,
            timeout=15,
            check=True,
            env=build_horizon_environment(build_dir),
            creationflags=resolve_creation_flags(sys.platform),
        )
        if len(response.stdout) > 64 * 1024:
            raise ValueError("oversized Launch API")
        fields = as_mapping(json.loads(response.stdout))
        if not (as_string(fields.get("launch_api")) or "").startswith("0.1."):
            raise ValueError("unsupported Launch API")
        return fields
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise InstanceError(f"Cannot read Horizon Launch API: {executable.name}") from exc


def _require_options(fields: dict[str, JsonValue], required: set[str]) -> None:
    available = {
        as_string(as_mapping(option).get("name")) for option in as_list(fields.get("options"))
    }
    if not required.issubset(available):
        raise InstanceError("Horizon Launch API does not support the required options")
