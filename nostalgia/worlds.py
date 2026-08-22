"""Đọc thế giới đơn (saves) và server (servers.dat) của từng instance.

Cả hai đều là NBT: `level.dat` nén gzip, `servers.dat` để trần. Ở đây có một
trình đọc NBT tối giản (đủ để lấy tên thế giới + lần chơi cuối, và danh sách
server) thay vì kéo thêm thư viện ngoài — ta chỉ cần vài trường.
"""

from __future__ import annotations

import base64
import gzip
import json
import re
import shutil
import socket
import struct
import zipfile
from pathlib import Path

from .instances import slug


def _safe_world_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip().strip(".")
    return name[:64] or "World"


def import_world_zip(zip_path: Path, saves_dir: Path) -> str:
    """Giải nén một world Minecraft từ file .zip vào <instance>/saves/<tên>.

    Tự nhận diện thư mục world (thư mục chứa level.dat, nông nhất) dù zip gói world
    ở gốc hay trong một thư mục con. Trả về tên world đã thêm.
    """
    zip_path, saves_dir = Path(zip_path), Path(saves_dir)
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        levels = [n for n in names if n.rsplit("/", 1)[-1] == "level.dat"]
        if not levels:
            raise ValueError("This zip has no level.dat — it isn't a Minecraft world.")
        levels.sort(key=lambda n: n.count("/"))
        root = levels[0][: -len("level.dat")]        # "" hoặc "MyWorld/"
        base = root.rstrip("/").rsplit("/", 1)[-1] if root else zip_path.stem
        dest = saves_dir / _safe_world_name(base)
        n = 2
        while dest.exists():                          # không đè world sẵn có
            dest = saves_dir / f"{_safe_world_name(base)} ({n})"; n += 1
        dest.mkdir(parents=True)
        for member in names:
            if root and not member.startswith(root):
                continue
            rel = member[len(root):] if root else member
            target = (dest / rel).resolve()
            if not str(target).startswith(str(dest.resolve())):
                continue                              # chặn zip-slip (../)
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
    return dest.name

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
            out.append({"kind": "world", "title": name, "folder": wd.name,
                        "instance": inst.name, "last": last})
    out.sort(key=lambda w: w["last"], reverse=True)
    return out[:limit]


_GAME_MODE = {0: "Survival", 1: "Creative", 2: "Adventure", 3: "Spectator"}


def _dir_size(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def list_worlds(saves_dir: Path) -> list[dict]:
    """Liệt kê world trong một thư mục saves, kèm icon + thông tin từ level.dat.

    Mỗi phần tử: {folder, title, last(ms), icon(bytes|None), size, mode, version,
    hardcore}. Sắp theo lần chơi gần nhất (mới nhất trước).
    """
    saves_dir = Path(saves_dir)
    out: list[dict] = []
    if not saves_dir.is_dir():
        return out
    for wd in saves_dir.iterdir():
        lvl = wd / "level.dat"
        if not (wd.is_dir() and lvl.is_file()):
            continue
        info = {"folder": wd.name, "title": wd.name, "icon": None,
                "last": int(lvl.stat().st_mtime * 1000), "size": _dir_size(wd),
                "mode": "", "version": "", "hardcore": False}
        try:
            data = parse_nbt(lvl.read_bytes()).get("Data", {})
            info["title"] = str(data.get("LevelName") or wd.name)
            lp = data.get("LastPlayed")
            if isinstance(lp, int) and lp > 0:
                info["last"] = lp
            info["mode"] = _GAME_MODE.get(data.get("GameType"), "")
            info["hardcore"] = bool(data.get("hardcore"))
            ver = data.get("Version")
            if isinstance(ver, dict):
                info["version"] = str(ver.get("Name", ""))
        except Exception:  # noqa: BLE001 — hỏng thì dùng tên thư mục + mtime
            pass
        icon = wd / "icon.png"
        if icon.is_file():
            try:
                info["icon"] = icon.read_bytes()
            except OSError:
                pass
        out.append(info)
    out.sort(key=lambda w: w["last"], reverse=True)
    return out


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
            icon = None
            raw_icon = s.get("icon")            # favicon base64 game đã cache
            if isinstance(raw_icon, str) and raw_icon:
                try:
                    icon = base64.b64decode(raw_icon.split(",")[-1])
                except Exception:  # noqa: BLE001
                    icon = None
            out.append({"kind": "server", "title": str(s.get("name") or ip or "Server"),
                        "ip": ip, "instance": inst.name, "last": mtime, "icon": icon})
    out.sort(key=lambda s: s["last"], reverse=True)
    return out[:limit]


# ---------- Server List Ping (lấy MOTD + số người + favicon trực tiếp) ----------

def _write_varint(value: int) -> bytes:
    out = bytearray()
    v = value & 0xFFFFFFFF
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _read_varint(sock: socket.socket) -> int:
    num = shift = 0
    for _ in range(5):
        d = sock.recv(1)
        if not d:
            raise OSError("kết nối đóng")
        b = d[0]
        num |= (b & 0x7F) << shift
        if not (b & 0x80):
            return num
        shift += 7
    raise OSError("varint quá dài")


def _flatten_motd(desc) -> str:
    if isinstance(desc, str):
        return desc
    if isinstance(desc, list):
        return "".join(_flatten_motd(e) for e in desc)
    if isinstance(desc, dict):
        s = desc.get("text", "")
        for e in desc.get("extra", []):
            s += _flatten_motd(e)
        return s
    return ""


def _strip_codes(s: str) -> str:
    """Bỏ mã màu §x của Minecraft, gộp nhiều khoảng trắng."""
    out = []
    skip = False
    for ch in s:
        if skip:
            skip = False
            continue
        if ch == "§":
            skip = True
            continue
        out.append(ch)
    return "".join(out)


def ping_server(address: str, timeout: float = 1.2) -> dict | None:
    """Truy vấn trạng thái máy chủ (giao thức 1.7+). Trả về MOTD/số người/favicon,
    hoặc None nếu không kết nối được. Best-effort — không hỗ trợ bản ghi SRV."""
    host, port = address, 25565
    if address.count(":") == 1:
        h, _, pt = address.partition(":")
        host = h
        try:
            port = int(pt)
        except ValueError:
            port = 25565
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except OSError:
        return None
    try:
        sock.settimeout(timeout)
        host_b = host.encode("utf-8")
        handshake = (b"\x00" + _write_varint(47) + _write_varint(len(host_b)) + host_b
                     + struct.pack(">H", port) + b"\x01")
        sock.sendall(_write_varint(len(handshake)) + handshake)
        sock.sendall(_write_varint(1) + b"\x00")     # status request
        _read_varint(sock)                            # tổng độ dài gói (bỏ qua)
        _read_varint(sock)                            # packet id (0)
        jlen = _read_varint(sock)
        buf = bytearray()
        while len(buf) < jlen:
            chunk = sock.recv(jlen - len(buf))
            if not chunk:
                break
            buf += chunk
        data = json.loads(bytes(buf).decode("utf-8", "replace"))
    except (OSError, ValueError):
        return None
    finally:
        sock.close()

    motd = _strip_codes(_flatten_motd(data.get("description", ""))).strip()
    motd = " ".join(motd.split())                     # gộp xuống dòng/khoảng trắng
    players = data.get("players") or {}
    fav = data.get("favicon")
    favicon = None
    if isinstance(fav, str) and "base64," in fav:
        try:
            favicon = base64.b64decode(fav.split("base64,", 1)[1])
        except Exception:  # noqa: BLE001
            favicon = None
    return {"motd": motd, "online": players.get("online"), "max": players.get("max"),
            "favicon": favicon}
