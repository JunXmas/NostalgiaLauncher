"""Forgotten Worlds đã gỡ khỏi launcher, nhưng bản chơi người dùng tạo từ nó vẫn chơi được.

Bản chơi FW cũ mang dấu vết: `.nostalgia-builtin-pack.json` ở thư mục đăng ký, file
`README-Forgotten-Worlds.txt` trong thư mục game, và có thể cả trường `modpackPreset` lạ trong
instance.json. Launcher mới phải coi nó như bản chơi thường: liệt kê được, chạy được, không
còn nút cập nhật modpack nào.
"""

from __future__ import annotations

import json
from pathlib import Path

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Instance
from source_tree import REPOSITORY_ROOT
from test_api import make_launcher

OLD_PRESET = "forgotten-" + "worlds"  # ghép chuỗi để test grep bên dưới không tự bắt mình


def test_old_server_pack_instance_still_lists_and_launches(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher.install_version(VERSION_ID)
    instance = launcher.create_instance(Instance(instance_id="fw", version_id=VERSION_ID))
    registry = launcher.paths.instance_dir("fw")
    (registry / ".nostalgia-builtin-pack.json").write_text(
        json.dumps({"format": 1, "preset": OLD_PRESET, "version": "1.0.5", "files": {}})
    )
    document = json.loads((registry / "instance.json").read_text())
    (registry / "instance.json").write_text(json.dumps({**document, "modpackPreset": OLD_PRESET}))
    game_dir = launcher.instance_game_dir(instance)
    (game_dir / "README-Forgotten-Worlds.txt").write_text("Forgotten Worlds — Optimized 1.0.5")
    launcher.add_offline_account("Jun")

    assert [listed.instance_id for listed in launcher.list_instances()] == ["fw"]
    lines: list[str] = []
    game = launcher.launch_instance("fw", "Jun", on_output=lines.append)
    assert game.wait(timeout=30) == 0
    assert any("fake java" in line for line in lines)


def test_no_forgotten_worlds_code_left_in_source_or_tests() -> None:
    needle = OLD_PRESET.replace("-", "")
    hits = [
        str(path.relative_to(REPOSITORY_ROOT))
        for directory in ("src", "tests", "bench", "packaging")
        for path in (REPOSITORY_ROOT / directory).rglob("*")
        if path.is_file()
        and path.suffix in {".py", ".qml", ".js", ".json", ".spec"}
        and path.name != Path(__file__).name
        and needle
        in path.read_text(encoding="utf-8", errors="ignore")
        .lower()
        .replace("-", "")
        .replace(" ", "")
    ]
    assert hits == []
