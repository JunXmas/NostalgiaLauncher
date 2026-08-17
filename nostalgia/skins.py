"""Đổi skin ngay trong launcher + lưu 5 skin gần nhất.

- Với tài khoản Microsoft sở hữu game: đẩy skin thật lên Mojang
  (PUT /minecraft/profile/skins) bằng access token của tài khoản.
- Luôn lưu lại 5 skin (file PNG 64x64) đã dùng gần nhất dưới CONFIG_DIR/skins
  để chọn lại nhanh.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

from .paths import CONFIG_DIR

SKINS_DIR = CONFIG_DIR / "skins"
DEFAULTS_DIR = SKINS_DIR / "defaults"
INDEX_PATH = SKINS_DIR / "recent.json"
MAX_RECENT = 5
TIMEOUT = 30
PROFILE_SKINS = "https://api.minecraftservices.com/minecraft/profile/skins"
_TEX = "http://textures.minecraft.net/texture"

# Skin mặc định của Mojang (URL texture ổn định). classic = tay 4px, slim = 3px.
DEFAULT_SKINS = [
    ("Steve", "classic", f"{_TEX}/31f477eb1a7beee631c2ca64d06f8f68fa93a3386d04452ab27f43acdf1b60cb"),
    ("Alex", "slim", f"{_TEX}/1abc803022d8300ab7578b189294cce39622d9a404cdc00d3feacfdf45be6981"),
]


def ensure_defaults() -> list[dict]:
    """Tải (một lần) & cache skin mặc định; trả [{name, variant, path}] cái nào có."""
    DEFAULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for name, variant, url in DEFAULT_SKINS:
        p = DEFAULTS_DIR / f"{name.lower()}.png"
        if not p.exists():
            try:
                r = requests.get(url, timeout=TIMEOUT,
                                 headers={"User-Agent": "NostalgiaLauncher"})
                if r.status_code == 200 and r.content[:2] == b"\x89P":
                    p.write_bytes(r.content)
            except requests.RequestException:
                pass
        if p.exists():
            out.append({"name": name, "variant": variant, "path": str(p)})
    return out


def _index() -> list[dict]:
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _write_index(items: list[dict]) -> None:
    SKINS_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(items, indent=2))


def recent() -> list[dict]:
    """5 skin gần nhất, mới nhất trước: [{file, variant, ts}] với file là đường dẫn tuyệt đối."""
    out = []
    for it in _index():
        p = SKINS_DIR / it["file"]
        if p.exists():
            out.append({"path": str(p), "variant": it.get("variant", "classic"),
                        "ts": it.get("ts", 0)})
    return out


def remember(png: bytes, variant: str = "classic") -> str:
    """Lưu skin vào lịch sử (khử trùng theo nội dung), giữ tối đa 5. Trả về đường dẫn file."""
    SKINS_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(png).hexdigest()[:16]
    fname = f"{digest}.png"
    (SKINS_DIR / fname).write_bytes(png)
    items = [it for it in _index() if it.get("file") != fname]
    items.insert(0, {"file": fname, "variant": variant, "ts": int(time.time())})
    # cắt còn 5, xoá file thừa
    keep, drop = items[:MAX_RECENT], items[MAX_RECENT:]
    for it in drop:
        (SKINS_DIR / it["file"]).unlink(missing_ok=True)
    _write_index(keep)
    return str(SKINS_DIR / fname)


def apply_to_mojang(access_token: str, png: bytes, *, slim: bool = False) -> None:
    """Đổi skin trên tài khoản Mojang/Microsoft (cần access token còn hạn của MC)."""
    r = requests.put(
        PROFILE_SKINS,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"variant": "slim" if slim else "classic"},
        files={"file": ("skin.png", png, "image/png")},
        timeout=TIMEOUT,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Mojang từ chối đổi skin ({r.status_code}): {r.text[:200]}")


def load_file(path: str | Path) -> bytes:
    return Path(path).read_bytes()
