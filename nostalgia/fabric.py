"""Cài Fabric loader.

Fabric meta trả về một "profile json" dùng `inheritsFrom` để trỏ về phiên bản
vanilla: nó chỉ chứa phần chênh lệch (mainClass, thư viện của loader, vài tham số
JVM). Launcher phải tự trộn hai JSON lại thành một bản đầy đủ.
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

META = "https://meta.fabricmc.net/v2"
TIMEOUT = 30


def list_game_versions(stable_only: bool = True) -> list[str]:
    data = requests.get(f"{META}/versions/game", timeout=TIMEOUT).json()
    return [v["version"] for v in data if v.get("stable") or not stable_only]


def list_loaders(stable_only: bool = True) -> list[str]:
    data = requests.get(f"{META}/versions/loader", timeout=TIMEOUT).json()
    return [v["version"] for v in data if v.get("stable") or not stable_only]


def latest_loader() -> str:
    loaders = list_loaders()
    if not loaders:
        raise RuntimeError("Fabric meta không trả về loader nào.")
    return loaders[0]


def profile_json(game_version: str, loader_version: str) -> dict:
    r = requests.get(
        f"{META}/versions/loader/{game_version}/{loader_version}/profile/json", timeout=TIMEOUT
    )
    if r.status_code == 400:
        raise RuntimeError(f"Fabric không hỗ trợ {game_version} với loader {loader_version}.")
    r.raise_for_status()
    return r.json()


def maven_path(coordinate: str) -> str:
    """`group:artifact:version[:classifier]` -> đường dẫn tương đối trong maven repo.

    Thư viện Fabric chỉ khai báo toạ độ maven chứ không kèm sẵn đường dẫn như
    thư viện của Mojang, nên phải tự dựng.
    """
    parts = coordinate.split(":")
    group, artifact, version = parts[0], parts[1], parts[2]
    classifier = f"-{parts[3]}" if len(parts) > 3 else ""
    return f"{group.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}{classifier}.jar"


def merge_inherited(meta: dict, load_parent) -> dict:
    """Trộn profile Fabric với JSON vanilla mà nó kế thừa.

    Thứ tự thư viện quan trọng: thư viện của loader phải đứng TRƯỚC vanilla trên
    classpath, vì Fabric thay thế một số lớp của game.
    """
    parent_id = meta.get("inheritsFrom")
    if not parent_id:
        return meta

    parent = merge_inherited(load_parent(parent_id), load_parent)
    merged = dict(parent)
    special = {"libraries", "arguments", "minecraftArguments", "inheritsFrom"}
    merged.update({k: v for k, v in meta.items() if k not in special})

    merged["libraries"] = list(meta.get("libraries", [])) + list(parent.get("libraries", []))

    parent_args = parent.get("arguments", {})
    child_args = meta.get("arguments", {})
    if parent_args or child_args:
        merged["arguments"] = {
            "game": list(parent_args.get("game", [])) + list(child_args.get("game", [])),
            "jvm": list(parent_args.get("jvm", [])) + list(child_args.get("jvm", [])),
        }
    elif "minecraftArguments" in parent:
        merged["minecraftArguments"] = meta.get("minecraftArguments",
                                                parent["minecraftArguments"])

    # Jar của game vẫn là jar vanilla; chỉ metadata là của Fabric.
    merged["jar"] = parent.get("jar", parent["id"])
    merged.pop("inheritsFrom", None)
    return merged


def install(installer, game_version: str, loader_version: str | None = None) -> str:
    """Ghi JSON phiên bản Fabric xuống đĩa và trả về id của nó."""
    loader_version = loader_version or latest_loader()
    profile = profile_json(game_version, loader_version)
    version_id = profile["id"]

    # Bảo đảm có JSON vanilla trước khi trộn.
    installer.version_json(game_version)

    target = installer.versions_dir / version_id / f"{version_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(profile, indent=2))
    return version_id
