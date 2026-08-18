"""Đọc thế giới đơn (saves) và server (servers.dat) của từng instance.

Cả hai đều là NBT: `level.dat` nén gzip, `servers.dat` để trần. Ở đây có một
trình đọc NBT tối giản (đủ để lấy tên thế giới + lần chơi cuối, và danh sách
server) thay vì kéo thêm thư viện ngoài — ta chỉ cần vài trường.
"""

from __future__ import annotations

import gzip
import struct
from pathlib import Path

from .instances import slug

# Mã tag NBT
_TAG_END = 0


class _Reader:
    def __init__(self, data: bytes):
        self.d = data
        self.p = 0

    def _unpack(self, fmt: str, size: int):
        v = struct.unpack_from(fmt, self.d, self.p)[0]
        self.p += size
        return v

    def u8(self) -> int:
        v = self.d[self.p]
        self.p += 1
        return v

    def string(self) -> str:
        n = self._unpack(">H", 2)
        s = self.d[self.p:self.p + n].decode("utf-8", "replace")
        self.p += n
        return s

    def payload(self, t: int):
        if t == 1:   # Byte
            return self._unpack(">b", 1)
        if t == 2:   # Short
            return self._unpack(">h", 2)
        if t == 3:   # Int
            return self._unpack(">i", 4)
        if t == 4:   # Long
            return self._unpack(">q", 8)
        if t == 5:   # Float
            return self._unpack(">f", 4)
        if t == 6:   # Double
            return self._unpack(">d", 8)
        if t == 7:   # Byte array
            n = self._unpack(">i", 4)
            v = self.d[self.p:self.p + n]
            self.p += n
            return v
        if t == 8:   # String
            return self.string()
        if t == 9:   # List
            it = self.u8()
            n = self._unpack(">i", 4)
            return [self.payload(it) for _ in range(max(0, n))]
        if t == 10:  # Compound
            out = {}
            while True:
                tt = self.u8()
                if tt == _TAG_END:
                    break
                name = self.string()
                out[name] = self.payload(tt)
            return out
        if t == 11:  # Int array
            n = self._unpack(">i", 4)
            v = list(struct.unpack_from(">%di" % n, self.d, self.p))
            self.p += 4 * n
            return v
        if t == 12:  # Long array
            n = self._unpack(">i", 4)
            v = list(struct.unpack_from(">%dq" % n, self.d, self.p))
            self.p += 8 * n
            return v
        raise ValueError(f"NBT tag lạ: {t}")


def parse_nbt(raw: bytes) -> dict:
    """Trả về compound gốc của một khối NBT (tự giải nén nếu là gzip)."""
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    r = _Reader(raw)
    tt = r.u8()
    if tt == _TAG_END:
        return {}
    r.string()             # tên compound gốc (thường rỗng)
    return r.payload(tt)


def _instance_dir(inst, game_root: Path) -> Path:
    return game_root / "instances" / slug(inst.name)


def recent_worlds(store, game_root: Path, limit: int = 8) -> list[dict]:
    """Thế giới đơn của mọi instance, sắp theo lần chơi cuối (mới nhất trước)."""
    out: list[dict] = []
    for inst in store.all():
        saves = _instance_dir(inst, game_root) / "saves"
        if not saves.is_dir():
            continue
        for wd in saves.iterdir():
            lvl = wd / "level.dat"
            if not lvl.is_file():
                continue
            name, last = wd.name, int(lvl.stat().st_mtime * 1000)
            try:
                root = parse_nbt(lvl.read_bytes())
                data = root.get("Data", root)
                name = str(data.get("LevelName") or wd.name)
                lp = data.get("LastPlayed")
                if isinstance(lp, int) and lp > 0:
                    last = lp
            except Exception:  # noqa: BLE001 — hỏng thì dùng mtime + tên thư mục
                pass
            out.append({"kind": "world", "title": name,
                        "instance": inst.name, "last": last})
    out.sort(key=lambda w: w["last"], reverse=True)
    return out[:limit]


def recent_servers(store, game_root: Path, limit: int = 8) -> list[dict]:
    """Server đã lưu của mọi instance (servers.dat). Không có mốc thời gian riêng
    nên xếp theo lần sửa file, giữ thứ tự trong danh sách multiplayer."""
    out: list[dict] = []
    for inst in store.all():
        sf = _instance_dir(inst, game_root) / "servers.dat"
        if not sf.is_file():
            continue
        try:
            root = parse_nbt(sf.read_bytes())
        except Exception:  # noqa: BLE001
            continue
        mtime = int(sf.stat().st_mtime * 1000)
        for s in root.get("servers", []):
            if not isinstance(s, dict):
                continue
            ip = str(s.get("ip", ""))
            out.append({"kind": "server", "title": str(s.get("name") or ip or "Server"),
                        "ip": ip, "instance": inst.name, "last": mtime})
    out.sort(key=lambda s: s["last"], reverse=True)
    return out[:limit]
