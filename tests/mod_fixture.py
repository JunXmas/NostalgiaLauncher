"""JAR tự tạo để kiểm checker và sửa mod, không dùng nội dung mod bên ngoài."""

import json
import zipfile
from pathlib import Path


def write_fabric(path: Path, mod_id: str, **fields: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "fabric.mod.json", json.dumps({"id": mod_id, "version": "1.0.0", **fields})
        )
