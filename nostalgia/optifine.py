"""Tải OptiFine từ nguồn CHÍNH THỨC (optifine.net) ngay trên máy người dùng.

Nguyên tắc đã chốt với dự án:
- KHÔNG mirror/redistribute — jar luôn tải trực tiếp từ optifine.net, không đi
  qua server hay GitHub Releases của launcher.
- GIỮ ad-view — mở trang ``adloadx`` rồi CHỜ vài giây (tôn trọng cơ chế của tác
  giả) trước khi lấy link ``downloadx``. Không cố skip quảng cáo.
- Chỉ dành cho instance LEGACY (Forge, Minecraft <= 1.12.2). Bản mới nên dùng
  Sodium/Iris (mã nguồn mở) thay cho OptiFine.

OptiFine đóng, không có API — parser dựa vào HTML của optifine.net nên CÓ THỂ vỡ
khi trang đổi. Gom hết chỗ dễ vỡ vào đúng file này để về sau chỉ phải vá một nơi.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import requests

BASE = "https://optifine.net"
HEADERS = {"User-Agent": "Mozilla/5.0 (NostalgiaLauncher)"}
TIMEOUT = 30

_FILE_RE = re.compile(r"adloadx\?f=(OptiFine_[^\"&]+\.jar)")
_DL_RE = re.compile(r"(downloadx\?f=[^\"'& ]+&x=[0-9a-fA-F]+)")
_MC_RE = re.compile(r"OptiFine_([0-9]+(?:\.[0-9]+)*)_")


def mc_of(filename: str) -> str:
    """'OptiFine_1.12.2_HD_U_G5.jar' -> '1.12.2'."""
    m = _MC_RE.match(filename)
    return m.group(1) if m else ""


def mc_from_version_id(version_id: str) -> str:
    """Rút phiên bản Minecraft từ id profile (vanilla/forge/fabric) — vd
    '1.12.2-forge-14.23.5.2859' -> '1.12.2'."""
    m = re.search(r"\b(1\.\d+(?:\.\d+)?)\b", version_id or "")
    return m.group(1) if m else ""


def is_legacy(mc_version: str) -> bool:
    """Legacy = Minecraft 1.12.x trở xuống (nơi OptiFine không có bản thay thế mở)."""
    m = re.match(r"1\.(\d+)", mc_version or "")
    return bool(m) and int(m.group(1)) <= 12


def versions() -> list[dict]:
    """Danh sách bản OptiFine [{file, mc}], theo thứ tự trang (mới -> cũ), đã khử trùng."""
    r = requests.get(f"{BASE}/downloads", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    seen: set[str] = set()
    out: list[dict] = []
    for f in _FILE_RE.findall(r.text):
        if f in seen:
            continue
        seen.add(f)
        out.append({"file": f, "mc": mc_of(f)})
    return out


def latest_for(mc_version: str) -> dict | None:
    """Bản OptiFine mới nhất khớp ĐÚNG một MC version (trang liệt kê mới nhất trước)."""
    for v in versions():
        if v["mc"] == mc_version:
            return v
    return None


def resolve_link(filename: str, *, ad_wait: float = 5.0, on_status=None) -> str:
    """URL downloadx thật, lấy từ trang adloadx — có CHỜ đủ thời gian quảng cáo."""
    if on_status:
        on_status("Opening OptiFine download page…")
    r = requests.get(f"{BASE}/adloadx", params={"f": filename},
                     headers={**HEADERS, "Referer": f"{BASE}/downloads"}, timeout=TIMEOUT)
    r.raise_for_status()
    m = _DL_RE.search(r.text)
    if not m:
        raise RuntimeError("OptiFine's page changed — couldn't find the download link.")
    if ad_wait > 0:
        if on_status:
            on_status(f"Respecting OptiFine's {int(ad_wait)}s ad view…")
        time.sleep(ad_wait)
    return f"{BASE}/{m.group(1)}"


def download(filename: str, dest: Path, *, ad_wait: float = 5.0,
             on_status=None, on_progress=None) -> Path:
    """Tải jar TRỰC TIẾP từ optifine.net về dest (ghi qua .part rồi đổi tên)."""
    url = resolve_link(filename, ad_wait=ad_wait, on_status=on_status)
    if on_status:
        on_status(f"Downloading {filename}…")
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, headers={**HEADERS, "Referer": f"{BASE}/adloadx?f={filename}"},
                      timeout=TIMEOUT, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(65536):
                if not chunk:
                    continue
                fh.write(chunk)
                done += len(chunk)
                if on_progress and total:
                    on_progress(done, total)
    with open(tmp, "rb") as fh:
        if fh.read(2) != b"PK":               # jar là file zip -> phải bắt đầu bằng 'PK'
            tmp.unlink(missing_ok=True)
            raise RuntimeError("The downloaded file wasn't a valid OptiFine jar.")
    tmp.replace(dest)
    return dest


def install_to_mods(filename: str, mods_dir: Path, **kw) -> Path:
    """Tải OptiFine thẳng vào thư mục mods của một instance Forge legacy."""
    return download(filename, Path(mods_dir) / filename, **kw)
