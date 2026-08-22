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

# classId của CurseForge cho từng loại nội dung (khớp 'kind' nội bộ của launcher).
CLASS_IDS = {"mods": 6, "resourcepacks": 12, "shaderpacks": 6552, "modpacks": _CLASS_MODPACK}
# sortField của CF: 1 Featured · 2 Popularity · 3 LastUpdated · 6 TotalDownloads.
_SORT = {"relevance": 2, "downloads": 6, "newest": 3}
# modLoaderType của CF (chỉ dùng cho mods).
_LOADER_TYPE = {"forge": 1, "fabric": 4, "quilt": 5, "neoforge": 6}


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


def search_content(query: str, kind: str = "modpacks", *, key: str = "",
                   backend: str = "", game_version: str | None = None,
                   loader: str | None = None, sort: str = "downloads",
                   page_size: int = 40, index: int = 0) -> dict:
    """Tìm nội dung CurseForge (mods/resourcepacks/shaderpacks/modpacks). Cần MỘT
    trong hai đường: key riêng của người dùng -> gọi thẳng api.curseforge.com; hoặc
    backend (Worker của launcher) -> {backend}/cf/mods/search (key ở server).
    Trả về {'hits': [...], 'total': N}; mỗi hit giống Modrinth để tái dùng UI thẻ."""
    params = {
        "gameId": _GAME_ID, "classId": CLASS_IDS.get(kind, _CLASS_MODPACK),
        "searchFilter": query, "pageSize": page_size, "index": index,
        "sortField": _SORT.get(sort, 2), "sortOrder": "desc",
    }
    if game_version:
        params["gameVersion"] = game_version
    if kind == "mods" and loader in _LOADER_TYPE:
        params["modLoaderType"] = _LOADER_TYPE[loader]
    if key:
        r = requests.get(f"{_API}/mods/search", params=params,
                         headers=_headers(key), timeout=25)
    elif backend:
        r = requests.get(f"{backend.rstrip('/')}/cf/mods/search", params=params,
                         headers={"Accept": "application/json"}, timeout=25)
    else:
        raise RuntimeError("CurseForge search needs an API key or a backend.")
    r.raise_for_status()
    body = r.json() or {}
    out = []
    for m in body.get("data") or []:
        authors = m.get("authors") or []
        versions = sorted({fi.get("gameVersion") for fi in (m.get("latestFilesIndexes") or [])
                           if fi.get("gameVersion")}, reverse=True)
        out.append({
            "project_id": m.get("id"),
            "slug": str(m.get("id")),          # khoá busy/done nội bộ
            "title": m.get("name", "?"),
            "author": (authors[0].get("name") if authors else ""),
            "description": m.get("summary", ""),
            "downloads": m.get("downloadCount", 0),
            "follows": m.get("thumbsUpCount", 0),
            "icon_url": (m.get("logo") or {}).get("url", ""),
            "featured_gallery": ((m.get("screenshots") or [{}])[0] or {}).get("url", ""),
            "date_modified": m.get("dateModified", ""),
            "categories": [c.get("name", "") for c in (m.get("categories") or [])],
            "versions": versions,
            "source": "curseforge",
        })
    total = ((body.get("pagination") or {}).get("totalCount")) or len(out)
    return {"hits": out, "total": total}


def search_modpacks(query: str, *, key: str = "", backend: str = "",
                    game_version: str | None = None,
                    page_size: int = 40, index: int = 0) -> list[dict]:
    """Tìm modpack (trả về list hit) — bọc quanh search_content cho trang modpack."""
    return search_content(query, "modpacks", key=key, backend=backend,
                          game_version=game_version, page_size=page_size,
                          index=index)["hits"]


def file_sha1(file_obj: dict) -> str | None:
    """Rút sha1 (algo 1) từ object file CurseForge, nếu có."""
    for h in file_obj.get("hashes") or []:
        if h.get("algo") == 1 and h.get("value"):
            return h["value"]
    return None


def best_content_file(project_id, kind: str, *, game_version: str | None = None,
                      loader: str | None = None, key: str = "") -> dict | None:
    """File phù hợp nhất để cài một mod/resourcepack/shader: khớp bản game và (với
    mods) loader; mới nhất trước. Dùng endpoint files keyless nên không cần key."""
    files = mod_files(project_id, key=key, game_version=game_version, page_size=50)
    ext = ".jar" if kind == "mods" else ".zip"
    cand = [f for f in files if str(f.get("fileName", "")).lower().endswith(ext)]
    if game_version:
        gv = [f for f in cand if game_version in (f.get("gameVersions") or [])]
        cand = gv or cand
    if kind == "mods" and loader:
        want = loader.capitalize()          # CF liệt kê loader trong gameVersions ("Fabric"…)
        ld = [f for f in cand if want in (f.get("gameVersions") or [])]
        cand = ld or cand
    if not cand:
        return None
    cand.sort(key=lambda f: (f.get("releaseType", 9) == 1, int(f.get("id", 0))), reverse=True)
    return cand[0]


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
