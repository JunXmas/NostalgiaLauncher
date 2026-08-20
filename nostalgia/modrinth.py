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
           index: str = "relevance",
           limit: int = 30) -> list[dict]:
    """Trả về danh sách 'hit' đã gọn: id, slug, title, description, author, icon_url…

    index: relevance | downloads (phổ biến) | follows | newest | updated.
    query rỗng + index=downloads = 'discover' các mod hot nhất.
    """
    params = {
        "query": query,
        "facets": _facets(project_type, loaders, game_versions),
        "limit": str(limit),
        "index": index,
    }
    r = requests.get(f"{BASE}/search", params=params, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json().get("hits", [])


def search_page(query: str, project_type: str = "mod", *,
                loaders: list[str] | None = None,
                game_versions: list[str] | None = None,
                index: str = "relevance",
                limit: int = 20, offset: int = 0) -> dict:
    """Như search() nhưng có phân trang: trả {hits, total, offset, limit}."""
    params = {
        "query": query,
        "facets": _facets(project_type, loaders, game_versions),
        "limit": str(limit),
        "offset": str(offset),
        "index": index,
    }
    r = requests.get(f"{BASE}/search", params=params, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    d = r.json()
    return {"hits": d.get("hits", []), "total": int(d.get("total_hits", 0)),
            "offset": int(d.get("offset", offset)), "limit": int(d.get("limit", limit))}


def fetch_icon(url: str) -> bytes:
    """Tải dữ liệu ảnh icon của một project (dùng cho ảnh preview)."""
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.content


def project(id_or_slug: str) -> dict:
    """Chi tiết đầy đủ một project (gồm 'body' mô tả dài dạng markdown)."""
    r = requests.get(f"{BASE}/project/{id_or_slug}", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def updates(hashes: list[str], *, loaders: list[str] | None = None,
            game_versions: list[str] | None = None) -> dict:
    """Bản mới nhất cho từng file mod (theo sha1), lọc loader + bản game.

    Gửi /version_files/update: trả về map {sha1_cũ: version_object_mới_nhất}.
    version_object có 'files' (kèm sha1) để so với bản đang cài mà biết có nên
    cập nhật không.
    """
    if not hashes:
        return {}
    body: dict = {"hashes": hashes, "algorithm": "sha1"}
    if loaders:
        body["loaders"] = loaders
    if game_versions:
        body["game_versions"] = game_versions
    r = requests.post(f"{BASE}/version_files/update", json=body,
                      headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def projects_for_hashes(hashes: list[str]) -> set[str]:
    """Tập project_id mà các file (theo sha1) thuộc về — để Browse biết mod nào
    đã cài rồi.

    /version_files trả map {sha1: version_object}; version_object.project_id là
    dự án trên Modrinth. Jar không phải của Modrinth (modpack tự đóng…) không có
    trong map nên bị bỏ qua — không đánh dấu nhầm."""
    if not hashes:
        return set()
    r = requests.post(f"{BASE}/version_files",
                      json={"hashes": list(hashes), "algorithm": "sha1"},
                      headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return {v.get("project_id") for v in r.json().values() if v.get("project_id")}


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


def best_version(id_or_slug: str, *,
                 loaders: list[str] | None = None,
                 game_versions: list[str] | None = None) -> dict | None:
    """Phiên bản mới nhất có file, khớp loader + bản game (kèm dependencies)."""
    for v in versions(id_or_slug, loaders=loaders, game_versions=game_versions):
        if pick_file(v):
            return v
    return None


def best_file(id_or_slug: str, *,
              loaders: list[str] | None = None,
              game_versions: list[str] | None = None) -> dict | None:
    """File tải phù hợp nhất: phiên bản mới nhất khớp loader + bản game.

    Trả về dict {url, filename, sha1, size} hoặc None nếu không có bản nào khớp.
    """
    v = best_version(id_or_slug, loaders=loaders, game_versions=game_versions)
    f = pick_file(v) if v else None
    if f:
        return {
            "url": f["url"],
            "filename": f["filename"],
            "sha1": f.get("hashes", {}).get("sha1"),
            "size": f.get("size", 0),
        }
    return None
