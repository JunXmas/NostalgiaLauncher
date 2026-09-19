"""SKlauncher: launcher bên thứ ba dùng lại chính `launcher_profiles.json` của bản chính thức.

Tách khỏi `launchers.py` vì file đó đã kịch trần 200 dòng code (GLOSSARY §1.5), và vì
SKlauncher là ca duy nhất phải đọc một file dùng chung với launcher khác — nó cần một dấu
nhận biết riêng chứ không chỉ một đường dẫn riêng.
"""

from __future__ import annotations

import json
import logging
import os
import platform
from pathlib import Path

from nostalgia.importing.model import Found, platform_dir
from nostalgia.modloader.model import detect_game_version, detect_loader_kind

logger = logging.getLogger(__name__)


def scan_sklauncher() -> list[Found]:
    """Tìm các installation của SKlauncher 3.2 trên máy.

    3.2 để profile ngay trong `.minecraft` dùng chung với launcher chính thức, nên đường dẫn
    không phân biệt được hai launcher. Dấu nhận biết là thư mục con `sklauncher/` — nơi nó
    ghi `sklauncher_logs.txt`. Thiếu dấu ấy thì thư mục là của bản chính thức, và
    `_scan_vanilla` đã lo phần đó rồi.

    SKlauncher 4.0 (còn beta, mã đóng) để instance ở nơi khác theo định dạng chưa công bố —
    chưa quét được. Đoán mò định dạng thì import ra bản chơi hỏng, tệ hơn là không thấy gì.
    """
    shared = platform_dir("~/.minecraft", "~/Library/Application Support/minecraft", ".minecraft")
    bases = [base for base in (shared,) if base is not None and (base / "sklauncher").is_dir()]
    if platform.system() == "Windows":
        # Bản cài bằng Setup: mọi thứ lẽ ra vào `.minecraft` nằm ở `%APPDATA%\sklauncher`.
        bases.append(Path(os.environ.get("APPDATA", "~")) / "sklauncher")
    found: list[Found] = []
    for base in bases:
        found.extend(load_sklauncher_profiles(base))
    return found


def load_sklauncher_profiles(base: Path) -> list[Found]:
    """Đọc từng installation trong `launcher_profiles.json` của một thư mục SKlauncher.

    Bỏ qua profile không nói ra bản game (`latest-release`, `latest-snapshot`): đó là con trỏ
    chứ không phải một bản, và import theo nó sẽ dựng ra bản chơi trỏ vào hư không.
    """
    profiles_json = base / "launcher_profiles.json"
    if not profiles_json.exists():
        return []
    found: list[Found] = []
    try:
        body = json.loads(profiles_json.read_text(encoding="utf-8"))
        profiles = body.get("profiles")
        for key, saved in (profiles if isinstance(profiles, dict) else {}).items():
            if not isinstance(saved, dict):
                continue
            version_id = saved.get("lastVersionId") or ""
            game_version = detect_game_version(version_id)
            if not game_version:
                logger.debug("bỏ qua profile SKlauncher %s: không rõ bản game", key)
                continue
            game_dir = Path(saved["gameDir"]) if saved.get("gameDir") else base
            instance_name = saved.get("name") or key
            loader_kind = detect_loader_kind(version_id)
            found.append(Found("SKlauncher", instance_name, game_dir, game_version, loader_kind))
    except Exception:
        logger.debug("lỗi khi đọc launcher_profiles.json của SKlauncher %s", base, exc_info=True)
    return found
