"""Cài modpack CurseForge (.zip) vào một instance.

File .zip của CurseForge chứa `manifest.json` (bản Minecraft + modloader + danh
sách {projectID, fileID}) và thư mục `overrides/` chép thẳng vào thư mục game.
Khác Modrinth, manifest CHỈ có ID chứ không kèm URL tải; ta hỏi endpoint công
khai của trang CurseForge để lấy tên file rồi dựng URL CDN từ fileID — không cần
API key. Mod nào không tra được thì bỏ qua êm và đếm lại để báo người dùng.
"""

from __future__ import annotations

import json
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from . import install

# manifest.minecraft.modLoaders[].id có dạng "forge-43.2.0" / "fabric-0.15.11"
# / "neoforge-21.1.9". Xét neoforge trước forge (tên bao nhau).
_LOADER_PREFIX = [
    ("neoforge", "neoforge"),
    ("forge", "forge"),
    ("fabric", "fabric"),
    ("quilt", "quilt"),
]

_FILE_API = "https://www.curseforge.com/api/v1/mods/{mod}/files/{file}"

# Hai đường vào CurseForge:
#  - _WWW: endpoint công khai của trang web, KHÔNG cần key, nhưng /search bị
#    Cloudflare chặn. Dùng được /mods/{id}/files (liệt kê file của 1 project).
#  - _API: API chính thức, CẦN key (x-api-key). Chỉ dùng khi người dùng tự thêm
#    key miễn phí ở Cài đặt — khi đó mới duyệt/tìm modpack được.
_WWW = "https://www.curseforge.com/api/v1"
_API = "https://api.curseforge.com/v1"
_GAME_ID = 432          # Minecraft
_CLASS_MODPACK = 4471   # phân loại "Modpacks"
_UA = "Mozilla/5.0 (compatible; NostalgiaLauncher)"


def _headers(key: str = "") -> dict:
    h = {"User-Agent": _UA, "Accept": "application/json"}
    if key:
        h["x-api-key"] = key
    return h


def mod_files(project_id, *, key: str = "", game_version: str | None = None,
              page_size: int = 50, session: requests.Session | None = None) -> list[dict]:
    """Danh sách file của một project (mới nhất trước). Có key thì qua API chính
    thức, không thì qua endpoint web công khai (vẫn chạy)."""
    sess = session or requests
    params = {"pageSize": page_size, "index": 0}
    if game_version:
        params["gameVersion"] = game_version
    base = _API if key else _WWW
    r = sess.get(f"{base}/mods/{project_id}/files", params=params,
                 headers=_headers(key), timeout=25)
    r.raise_for_status()
    return (r.json() or {}).get("data") or []


def best_modpack_file(project_id, *, key: str = "",
                      game_version: str | None = None) -> dict | None:
    """File modpack (.zip) phù hợp nhất: ưu tiên bản release, mới nhất trước."""
    files = mod_files(project_id, key=key, game_version=game_version)
    zips = [f for f in files if str(f.get("fileName", "")).lower().endswith(".zip")]
    if game_version:
        matched = [f for f in zips if game_version in (f.get("gameVersions") or [])]
        zips = matched or zips
    if not zips:
        return None
    # releaseType 1 = release; xếp release lên trước, rồi theo id (mới hơn = lớn hơn).
    zips.sort(key=lambda f: (f.get("releaseType", 9) == 1, int(f.get("id", 0))),
              reverse=True)
    return zips[0]


def file_url(file_id, file_name: str, download_url: str | None = None) -> str:
    """URL tải: dùng downloadUrl nếu có (bản API có key), không thì dựng CDN."""
    return download_url or _cdn_url(int(file_id), file_name)


def search_modpacks(query: str, *, key: str, game_version: str | None = None,
                    page_size: int = 40, index: int = 0) -> list[dict]:
    """Tìm modpack trên CurseForge (CẦN key). Trả về dạng 'hit' giống Modrinth để
    tái dùng UI thẻ: title/author/description/downloads/icon_url/project_id..."""
    params = {
        "gameId": _GAME_ID, "classId": _CLASS_MODPACK,
        "searchFilter": query, "pageSize": page_size, "index": index,
        "sortField": 2, "sortOrder": "desc",   # 2 = Popularity
    }
    if game_version:
        params["gameVersion"] = game_version
    r = requests.get(f"{_API}/mods/search", params=params,
                     headers=_headers(key), timeout=25)
    r.raise_for_status()
    out = []
    for m in (r.json() or {}).get("data") or []:
        authors = m.get("authors") or []
        out.append({
            "project_id": m.get("id"),
            "title": m.get("name", "?"),
            "author": (authors[0].get("name") if authors else ""),
            "description": m.get("summary", ""),
            "downloads": m.get("downloadCount", 0),
            "follows": m.get("thumbsUpCount", 0),
            "icon_url": (m.get("logo") or {}).get("url", ""),
            "featured_gallery": ((m.get("screenshots") or [{}])[0] or {}).get("url", ""),
            "date_modified": m.get("dateModified", ""),
            "categories": [c.get("name", "") for c in (m.get("categories") or [])],
            "source": "curseforge",
        })
    return out


def read_manifest(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as z:
        return json.loads(z.read("manifest.json"))


def is_curseforge(path: Path) -> bool:
    """File này có phải modpack CurseForge (zip chứa manifest.json) không?"""
    try:
        with zipfile.ZipFile(path) as z:
            if "manifest.json" not in z.namelist():
                return False
            m = json.loads(z.read("manifest.json"))
    except (OSError, zipfile.BadZipFile, ValueError):
        return False
    return m.get("manifestType") == "minecraftModpack" or "minecraft" in m


def loader_and_mc(manifest: dict) -> tuple[str, str]:
    """(loader, phiên_bản_minecraft) từ manifest CurseForge."""
    mc_block = manifest.get("minecraft", {}) or {}
    mc = mc_block.get("version", "")
    ids = [ld.get("id", "") for ld in (mc_block.get("modLoaders") or [])]
    for prefix, loader in _LOADER_PREFIX:
        if any(i.startswith(prefix) for i in ids):
            return loader, mc
    return "vanilla", mc


def _cdn_url(file_id: int, file_name: str) -> str:
    """URL CDN forgecdn: files/<id//1000>/<id%1000>/<tên file>."""
    return (f"https://mediafilez.forgecdn.net/files/"
            f"{file_id // 1000}/{file_id % 1000}/{file_name}")


def _resolve(project_id: int, file_id: int,
             session: requests.Session) -> tuple[str, str] | None:
    """Trả về (url, filename) để tải một mod, hoặc None nếu không tra được."""
    try:
        r = session.get(_FILE_API.format(mod=project_id, file=file_id), timeout=25)
        if r.status_code != 200:
            return None
        data = (r.json() or {}).get("data") or {}
    except (requests.RequestException, ValueError):
        return None
    name = data.get("fileName")
    if not name:
        return None
    # Có downloadUrl thì dùng luôn; không thì dựng URL CDN từ fileID.
    return data.get("downloadUrl") or _cdn_url(file_id, name), name


def install_contents(zip_path: Path, game_dir: Path,
                     on_status=None, on_progress=None) -> dict:
    """Bung overrides và tải toàn bộ mod của pack (song song) vào game_dir.

    Trả về manifest, thêm khoá '_skipped' = số mod không tải được (để báo UI).
    """
    game_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        manifest = json.loads(z.read("manifest.json"))
        override_dir = (manifest.get("overrides") or "overrides").rstrip("/") + "/"
        for name in z.namelist():
            if name.startswith(override_dir) and not name.endswith("/"):
                dest = game_dir / name[len(override_dir):]
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(z.read(name))

    files = [f for f in manifest.get("files", [])
             if f.get("projectID") and f.get("fileID")]
    total = len(files)
    if on_status:
        on_status(f"Downloading {total} mods from CurseForge…")
    if on_progress:
        on_progress(0, total)

    mods_dir = game_dir / "mods"
    mods_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    done = [0]
    skipped = [0]
    lock = threading.Lock()

    def one(f):
        ok = False
        got = _resolve(int(f["projectID"]), int(f["fileID"]), session)
        if got:
            url, name = got
            try:
                install.download(url, mods_dir / name)   # manifest không kèm hash
                ok = True
            except (OSError, requests.RequestException, RuntimeError):
                ok = False
        with lock:
            if ok:
                done[0] += 1
            else:
                skipped[0] += 1
            if on_progress:
                on_progress(done[0] + skipped[0], total)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(one, files))
    manifest["_skipped"] = skipped[0]
    return manifest
