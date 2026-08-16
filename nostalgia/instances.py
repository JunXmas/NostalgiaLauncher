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


def slug(name: str) -> str:
    """Tên thư mục an toàn từ tên hiển thị (giữ chữ/số/gạch, gộp khoảng trắng)."""
    s = re.sub(r"[^\w.-]+", "-", name.strip(), flags=re.UNICODE).strip("-.")
    return s or "instance"


@dataclass
class Instance:
    name: str        # tên hiển thị (duy nhất)
    version: str     # id phiên bản để chạy (vanilla hoặc fabric-loader-...)

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
        self.instances = [Instance(**i) for i in raw.get("instances", [])
                          if i.get("name") and i.get("version")]
        self.active = raw.get("active", "")

    def _save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {"active": self.active,
                "instances": [asdict(i) for i in self.instances]}
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)

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

    def active_instance(self) -> Instance | None:
        return self.get(self.active) or (self.instances[0] if self.instances else None)
