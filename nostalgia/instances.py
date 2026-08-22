"""Instance = một 'modpack' riêng: có thư mục game riêng (mods/saves/config/
resourcepacks tách biệt) nhưng dùng chung kho versions/libraries/assets.

Nhờ vậy cài mod cho instance này không đụng instance kia. Mỗi instance chỉ gồm
một cái tên và phiên bản Minecraft để chạy; thư mục của nó nằm ở
<game_dir>/instances/<slug>.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .paths import CONFIG_DIR

INSTANCES_PATH = CONFIG_DIR / "instances.json"


def pretty_version(version: str) -> str:
    """Đổi id phiên bản kỹ thuật thành tên thân thiện cho người phổ thông:
    'fabric-loader-0.19.3-1.21.11' -> '1.21.11 · Fabric';
    '1.12.2-forge-14.23.5.2859'    -> '1.12.2 · Forge'; '1.20.1' -> '1.20.1'."""
    v = (version or "").strip()
    low = v.lower()
    loader = next((disp for name, disp in (
        ("neoforge", "NeoForge"), ("fabric", "Fabric"),
        ("quilt", "Quilt"), ("forge", "Forge")) if name in low), "")
    if "fabric-loader" in low or "quilt-loader" in low:
        mc = v.rsplit("-", 1)[-1]            # mc nằm ở đuôi
    else:
        m = re.match(r"^(\d+\.\d+(?:\.\d+)?)", v)   # '1.12.2-forge-…' hoặc '1.20.1'
        mc = m.group(1) if m else v
    return f"{mc} · {loader}" if (loader and mc) else (mc or v)


def slug(name: str) -> str:
    """Tên thư mục an toàn từ tên hiển thị (giữ chữ/số/gạch, gộp khoảng trắng)."""
    s = re.sub(r"[^\w.-]+", "-", name.strip(), flags=re.UNICODE).strip("-.")
    return s or "instance"


@dataclass
class Instance:
    name: str            # tên hiển thị (duy nhất)
    version: str         # id phiên bản để chạy (vanilla hoặc fabric-loader-...)
    memory_mb: int = 0     # RAM riêng; 0 = dùng mặc định chung
    java_path: str = ""    # Java riêng; rỗng = dùng mặc định chung
    playtime_sec: int = 0  # tổng thời gian chơi (giây)
    last_played: str = ""  # ngày chơi gần nhất (YYYY-MM-DD)

    def dir(self, game_root: Path) -> Path:
        return game_root / "instances" / slug(self.name)


class InstanceStore:
    def __init__(self, path: Path | None = None):
        self.path = path or INSTANCES_PATH
        self.instances: list[Instance] = []
        self.active: str = ""
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return
        # Chịu được lệch schema: bỏ qua key lạ (bản khác ghi thêm) và entry hỏng,
        # để MỘT bản ghi lỗi không làm bay SẠCH instance -> tránh mất dữ liệu.
        known = set(Instance.__dataclass_fields__)
        out = []
        for i in raw.get("instances", []):
            if not (i.get("name") and i.get("version")):
                continue
            try:
                out.append(Instance(**{k: v for k, v in i.items() if k in known}))
            except (TypeError, ValueError):
                continue
        self.instances = out
        self.active = raw.get("active", "")

    def _save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {"active": self.active,
                "instances": [asdict(i) for i in self.instances]}
        # Ghi atomic: ghi ra file tạm rồi os.replace — nếu bị kill giữa chừng
        # (vd update khởi động lại app) thì instances.json KHÔNG bị cắt về rỗng.
        tmp = self.path.with_suffix(".json.tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)

    def all(self) -> list[Instance]:
        return list(self.instances)

    def get(self, name: str) -> Instance | None:
        return next((i for i in self.instances if i.name == name), None)

    def unique_name(self, base: str) -> str:
        """Tên chưa bị trùng: 'Fun', 'Fun 2', 'Fun 3'…"""
        base = base.strip() or "Instance"
        if not self.get(base):
            return base
        n = 2
        while self.get(f"{base} {n}"):
            n += 1
        return f"{base} {n}"

    def add(self, name: str, version: str) -> Instance:
        inst = Instance(name=self.unique_name(name), version=version)
        self.instances.append(inst)
        if not self.active:
            self.active = inst.name
        self._save()
        return inst

    def remove(self, name: str) -> None:
        self.instances = [i for i in self.instances if i.name != name]
        if self.active == name:
            self.active = self.instances[0].name if self.instances else ""
        self._save()

    def set_active(self, name: str) -> None:
        if self.get(name):
            self.active = name
            self._save()

    def set_version(self, name: str, version: str) -> None:
        """Đổi id phiên bản để chạy của một instance (dùng khi cập nhật modpack)."""
        inst = self.get(name)
        if inst and version and inst.version != version:
            inst.version = version
            self._save()

    def set_settings(self, name: str, *, memory_mb: int, java_path: str) -> None:
        inst = self.get(name)
        if inst:
            inst.memory_mb = memory_mb
            inst.java_path = java_path
            self._save()

    def add_playtime(self, name: str, seconds: float) -> None:
        import datetime
        inst = self.get(name)
        if inst and seconds > 0:
            inst.playtime_sec += int(seconds)
            inst.last_played = datetime.date.today().isoformat()
            self._save()

    def rename(self, old: str, new: str) -> str:
        """Đổi tên instance (bỏ trùng). Trả về tên mới thực tế; '' nếu không đổi."""
        inst = self.get(old)
        new = new.strip()
        if not inst or not new or new == old:
            return ""
        inst.name = self.unique_name(new)
        if self.active == old:
            self.active = inst.name
        self._save()
        return inst.name

    def active_instance(self) -> Instance | None:
        return self.get(self.active) or (self.instances[0] if self.instances else None)
