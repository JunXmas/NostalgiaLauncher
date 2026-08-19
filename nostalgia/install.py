"""Tải và cài đặt một phiên bản Minecraft: client.jar, libraries, natives, assets."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import shutil
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from .fabric import maven_path, merge_inherited

VERSION_MANIFEST = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
RESOURCES_BASE = "https://resources.download.minecraft.net"
TIMEOUT = 60

_OS_NAMES = {"Linux": "linux", "Darwin": "osx", "Windows": "windows"}
CURRENT_OS = _OS_NAMES.get(platform.system(), "linux")
_ARCH_NAMES = {"x86_64": "x86_64", "AMD64": "x86_64", "aarch64": "arm64", "arm64": "arm64"}
CURRENT_ARCH = _ARCH_NAMES.get(platform.machine(), "x86_64")


def rules_allow(rules: list[dict] | None, features: dict[str, bool] | None = None) -> bool:
    """Đánh giá mảng `rules` của Mojang. Rule sau ghi đè rule trước."""
    if not rules:
        return True
    features = features or {}
    allowed = False
    for rule in rules:
        applies = True
        os_spec = rule.get("os", {})
        if "name" in os_spec and os_spec["name"] != CURRENT_OS:
            applies = False
        if "arch" in os_spec and os_spec["arch"] not in (CURRENT_ARCH, platform.machine()):
            applies = False
        if "version" in os_spec and not re.search(os_spec["version"], platform.release()):
            applies = False
        for key, want in rule.get("features", {}).items():
            if bool(features.get(key, False)) != bool(want):
                applies = False
        if applies:
            allowed = rule["action"] == "allow"
    return allowed


def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, sha1: str | None = None, *, attempts: int = 4) -> Path:
    """Tải nếu thiếu hoặc sai hash. Có sha1 nên luôn kiểm tra để tự sửa file hỏng.

    Thử lại vài lần với backoff: server Mojang hay rớt kết nối khi tải hàng nghìn
    asset nhỏ song song (RemoteDisconnected), một cú rớt không nên làm hỏng cả lần cài.
    """
    if dest.exists() and (sha1 is None or _sha1(dest) == sha1):
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            with requests.get(url, stream=True, timeout=TIMEOUT) as r:
                r.raise_for_status()
                # Tên tạm riêng theo luồng: nếu hai job cùng đích chạy song song
                # (asset index đời cũ có nhiều tên trỏ cùng hash) thì không giẫm .part nhau.
                tmp = dest.with_suffix(f"{dest.suffix}.{threading.get_ident()}.part")
                with tmp.open("wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk)
                tmp.replace(dest)
            if sha1 and _sha1(dest) != sha1:
                raise RuntimeError(f"Hash không khớp sau khi tải: {dest}")
            return dest
        except (requests.RequestException, RuntimeError) as e:
            last = e
            if attempt < attempts - 1:
                time.sleep(0.5 * (attempt + 1))
    raise last if last else RuntimeError(f"Không tải được: {url}")


class Installer:
    def __init__(self, game_dir: Path, on_progress=None, *, store_root: Path | None = None):
        # game_dir = thư mục game khi chạy (mods/saves/--gameDir) — riêng từng
        # instance. store_root = kho versions/libraries/assets dùng chung; mặc
        # định trùng game_dir để giữ tương thích với chỗ gọi cũ.
        self.game_dir = game_dir
        root = store_root or game_dir
        self.store_root = root       # nơi đặt runtime/JRE dùng chung
        self.versions_dir = root / "versions"
        self.libraries_dir = root / "libraries"
        self.assets_dir = root / "assets"
        # on_progress(stage: str, done: int, total: int) — GUI nối vào đây;
        # CLI để None và chỉ in ra như cũ.
        self.on_progress = on_progress
        self._lock = threading.Lock()

    def _run_jobs(self, stage: str, jobs: list) -> None:
        """Tải song song, đếm tiến trình an toàn giữa các luồng."""
        total = len(jobs)
        done = 0
        if self.on_progress:
            self.on_progress(stage, 0, total)

        def one(job):
            nonlocal done
            download(*job)
            with self._lock:
                done += 1
                if self.on_progress:
                    self.on_progress(stage, done, total)

        with ThreadPoolExecutor(max_workers=12) as pool:
            list(pool.map(one, jobs))

    # ---------- version metadata ----------

    def list_versions(self, kind: str = "release") -> list[str]:
        manifest = requests.get(VERSION_MANIFEST, timeout=TIMEOUT).json()
        return [v["id"] for v in manifest["versions"] if kind == "all" or v["type"] == kind]

    def version_json(self, version_id: str) -> dict:
        """JSON đã trộn kế thừa — dùng cho mọi việc cài đặt và khởi động."""
        return merge_inherited(self._raw_version_json(version_id), self._raw_version_json)

    def offline_version_json(self, version_id: str) -> dict:
        """Như version_json nhưng tuyệt đối không chạm mạng.

        version_json() sẽ lặng lẽ gọi manifest của Mojang khi thiếu JSON dưới đĩa;
        lúc mất mạng điều đó biến thành ConnectionError vô nghĩa với người dùng.
        Ở đường chạy offline ta muốn hỏng sớm và nói rõ thiếu đúng file nào.
        """
        def strict(vid: str) -> dict:
            local = self.versions_dir / vid / f"{vid}.json"
            if not local.exists():
                raise FileNotFoundError(
                    f"Version metadata is missing: {local}\n"
                    f"Run once with an Internet connection to download {vid}."
                )
            return json.loads(local.read_text())

        return merge_inherited(strict(version_id), strict)

    def _raw_version_json(self, version_id: str) -> dict:
        local = self.versions_dir / version_id / f"{version_id}.json"
        if local.exists():
            data = json.loads(local.read_text())
            # JSON hợp lệ phải có 'downloads' (bản gốc Mojang) hoặc 'inheritsFrom'
            # (Fabric/Forge). Thiếu cả hai -> file cụt/hỏng, tải lại cho lành thay
            # vì để KeyError('downloads') làm chết cả lần cài.
            if "downloads" in data or "inheritsFrom" in data:
                return data
        manifest = requests.get(VERSION_MANIFEST, timeout=TIMEOUT).json()
        entry = next((v for v in manifest["versions"] if v["id"] == version_id), None)
        if entry is None:
            raise ValueError(f"Không tìm thấy phiên bản {version_id!r}")
        data = requests.get(entry["url"], timeout=TIMEOUT).json()
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(json.dumps(data, indent=2))
        return data

    def installed_versions(self) -> list[dict]:
        """Các phiên bản đã tải về đĩa. Dung lượng chỉ tính thư mục version:
        libraries và assets dùng chung nên quy cho một phiên bản là sai."""
        out = []
        if not self.versions_dir.exists():
            return out
        for d in sorted(self.versions_dir.iterdir()):
            meta_file = d / f"{d.name}.json"
            if not meta_file.is_file():
                continue
            try:
                meta = json.loads(meta_file.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            parent = meta.get("inheritsFrom")
            loader = "Fabric" if d.name.startswith("fabric-loader") else ""
            java = meta.get("javaVersion", {}).get("majorVersion")
            if java is None and parent:
                # Bản mod loader không tự khai javaVersion, phải hỏi bản gốc.
                try:
                    java = self._raw_version_json(parent).get(
                        "javaVersion", {}).get("majorVersion", 8)
                except Exception:  # noqa: BLE001 - thiếu metadata thì đoán Java 8
                    java = 8
            out.append({
                "id": d.name,
                "type": loader or meta.get("type", "?"),
                "java": java or 8,
                "size": size,
                "loader": loader,
                "parent": parent or "",
                # Bản Fabric dùng jar của bản gốc, nên phải kiểm ở đúng chỗ đó.
                "complete": (self.versions_dir / (parent or d.name)
                             / f"{parent or d.name}.jar").is_file(),
            })
        return sorted(out, key=lambda v: v["id"], reverse=True)

    def delete_version(self, version_id: str) -> bool:
        target = self.versions_dir / version_id
        if not target.is_dir():
            return False
        shutil.rmtree(target)
        return True

    # ---------- các thành phần ----------

    def _install_client(self, meta: dict) -> Path:
        art = meta["downloads"]["client"]
        dest = self.client_jar(meta)
        print("  client.jar ...")
        return download(art["url"], dest, art["sha1"])

    def _artifact_of(self, lib: dict) -> tuple[str, Path, str | None] | None:
        """(url, đích, sha1) cho một thư viện, hoặc None nếu nó không có jar chính.

        Mojang khai báo sẵn `downloads.artifact`; Fabric chỉ cho toạ độ maven cùng
        một `url` gốc, phải tự dựng đường dẫn.
        """
        artifact = lib.get("downloads", {}).get("artifact")
        if artifact:
            return artifact["url"], self.libraries_dir / artifact["path"], artifact.get("sha1")
        if lib.get("url") and lib.get("name"):
            rel = maven_path(lib["name"])
            return lib["url"].rstrip("/") + "/" + rel, self.libraries_dir / rel, lib.get("sha1")
        return None

    def client_jar(self, meta: dict) -> Path:
        """Jar của game. Bản Fabric dùng lại jar vanilla qua khoá `jar`."""
        jar_id = meta.get("jar", meta["id"])
        return self.versions_dir / jar_id / f"{jar_id}.jar"

    def library_paths(self, meta: dict) -> list[Path]:
        """Các jar cần đưa vào classpath (đã lọc theo OS), giữ nguyên thứ tự khai báo."""
        paths, seen = [], set()
        for lib in meta["libraries"]:
            if not rules_allow(lib.get("rules")):
                continue
            if "natives" in lib:
                continue  # jar natives không nằm trên classpath
            entry = self._artifact_of(lib)
            if entry and entry[1] not in seen:
                seen.add(entry[1])
                paths.append(entry[1])
        return paths

    def _install_libraries(self, meta: dict) -> None:
        jobs = []
        for lib in meta["libraries"]:
            if not rules_allow(lib.get("rules")):
                continue
            downloads = lib.get("downloads", {})
            if entry := self._artifact_of(lib):
                jobs.append(entry)
            # Định dạng cũ: natives nằm trong classifiers.
            if natives := lib.get("natives"):
                classifier = natives.get(CURRENT_OS, "").replace("${arch}", "64")
                native_art = downloads.get("classifiers", {}).get(classifier)
                if native_art:
                    jobs.append(
                        (native_art["url"], self.libraries_dir / native_art["path"], native_art["sha1"])
                    )
        print(f"  {len(jobs)} libraries ...")
        self._run_jobs("Đang tải thư viện", jobs)

    def natives_dir(self, meta: dict) -> Path:
        return self.versions_dir / meta["id"] / "natives"

    def _extract_natives(self, meta: dict) -> None:
        out = self.natives_dir(meta)
        out.mkdir(parents=True, exist_ok=True)
        for lib in meta["libraries"]:
            if not rules_allow(lib.get("rules")) or "natives" not in lib:
                continue
            classifier = lib["natives"].get(CURRENT_OS, "").replace("${arch}", "64")
            art = lib.get("downloads", {}).get("classifiers", {}).get(classifier)
            if not art:
                continue
            exclude = lib.get("extract", {}).get("exclude", [])
            with zipfile.ZipFile(self.libraries_dir / art["path"]) as z:
                for name in z.namelist():
                    if name.endswith("/") or name.startswith("META-INF/"):
                        continue
                    if any(name.startswith(pref) for pref in exclude):
                        continue
                    target = out / Path(name).name
                    if not target.exists():
                        target.write_bytes(z.read(name))

    def _install_assets(self, meta: dict) -> str:
        index_info = meta["assetIndex"]
        index_path = self.assets_dir / "indexes" / f"{index_info['id']}.json"
        download(index_info["url"], index_path, index_info["sha1"])
        index = json.loads(index_path.read_text())
        objects = index["objects"]

        # Khử trùng theo hash: index đời cũ (vd 1.12.2) liệt kê nhiều tên trỏ cùng
        # một object, không lọc sẽ tải trùng và hai luồng đua nhau ghi cùng file.
        jobs = []
        seen: set[str] = set()
        for obj in objects.values():
            h = obj["hash"]
            if h in seen:
                continue
            seen.add(h)
            jobs.append((f"{RESOURCES_BASE}/{h[:2]}/{h}", self.assets_dir / "objects" / h[:2] / h, h))
        print(f"  {len(jobs)} assets ...")
        self._run_jobs("Đang tải assets", jobs)

        # Bản cũ (1.7 trở về trước) đọc assets theo tên file thật, không theo hash.
        if index.get("virtual") or index.get("map_to_resources"):
            root = (
                self.game_dir / "resources"
                if index.get("map_to_resources")
                else self.assets_dir / "virtual" / index_info["id"]
            )
            for name, obj in objects.items():
                h = obj["hash"]
                target = root / name
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes((self.assets_dir / "objects" / h[:2] / h).read_bytes())

        return index_info["id"]

    def install(self, version_id: str) -> dict:
        meta = self.version_json(version_id)
        print(f"Installing {version_id} (needs Java {meta.get('javaVersion', {}).get('majorVersion', 8)}):")
        self._install_client(meta)
        self._install_libraries(meta)
        self._extract_natives(meta)
        self._install_assets(meta)
        print("Done.")
        return meta
