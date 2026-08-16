"""Thư viện nội dung Modrinth: tìm và lấy thông tin mod / resource pack.

API công khai v2 (https://docs.modrinth.com). Modrinth yêu cầu User-Agent nêu
rõ ứng dụng, nên mình gắn sẵn. Việc tải file để module mods.py lo, tái dùng
install.download() cho phần kiểm tra hash.
"""

from __future__ import annotations

import json

import requests

BASE = "https://api.modrinth.com/v2"
TIMEOUT = 25
HEADERS = {
    "User-Agent": "NostalgiaLauncher/0.2.0 (github.com/JunXmas/NostalgiaLauncher)",
}


def _facets(project_type: str, loaders: list[str] | None,
            game_versions: list[str] | None) -> str:
    groups: list[list[str]] = [[f"project_type:{project_type}"]]
    if loaders:
        groups.append([f"categories:{lo}" for lo in loaders])
    if game_versions:
        groups.append([f"versions:{v}" for v in game_versions])
    return json.dumps(groups)


def search(query: str, project_type: str = "mod", *,
           loaders: list[str] | None = None,
           game_versions: list[str] | None = None,
           limit: int = 30) -> list[dict]:
    """Trả về danh sách 'hit' đã gọn: id, slug, title, description, author…"""
    params = {
        "query": query,
        "facets": _facets(project_type, loaders, game_versions),
        "limit": str(limit),
        "index": "relevance",
    }
    r = requests.get(f"{BASE}/search", params=params, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json().get("hits", [])


def versions(id_or_slug: str, *,
             loaders: list[str] | None = None,
             game_versions: list[str] | None = None) -> list[dict]:
    """Danh sách phiên bản của một project, lọc theo loader và bản game nếu có."""
    params = {}
    if loaders:
        params["loaders"] = json.dumps(loaders)
    if game_versions:
        params["game_versions"] = json.dumps(game_versions)
    r = requests.get(f"{BASE}/project/{id_or_slug}/version",
                     params=params, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def pick_file(version: dict) -> dict | None:
    """Chọn file chính của một phiên bản (ưu tiên primary), kèm url/tên/hash."""
    files = version.get("files", [])
    if not files:
        return None
    return next((f for f in files if f.get("primary")), files[0])


def best_file(id_or_slug: str, *,
              loaders: list[str] | None = None,
              game_versions: list[str] | None = None) -> dict | None:
    """File tải phù hợp nhất: phiên bản mới nhất khớp loader + bản game.

    Trả về dict {url, filename, sha1, size} hoặc None nếu không có bản nào khớp.
    """
    for v in versions(id_or_slug, loaders=loaders, game_versions=game_versions):
        f = pick_file(v)
        if f:
            return {
                "url": f["url"],
                "filename": f["filename"],
                "sha1": f.get("hashes", {}).get("sha1"),
                "size": f.get("size", 0),
            }
    return None
