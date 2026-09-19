"""Hộp thoại Nhập bản chơi: bản chơi tìm được phải lên tới danh sách trên màn hình.

Vì sao đáng có: `tests/importing/test_launchers.py` chỉ chứng minh scanner trả đúng dữ liệu.
Nó không nói gì về việc dữ liệu ấy có tới được mắt người dùng hay không — mà triệu chứng người
dùng báo lại đúng là nhìn thấy "Không tìm thấy launcher nào trên máy". Test này đi trọn đường
scanner → importBridge → QML.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from test_bridges import wait_until
from test_qml import make_launcher

from nostalgia.ui.app import build_view

pytestmark = pytest.mark.usefixtures("qt_app")


def _make_flatpak_prism_instance(home: Path, name: str, game_version: str) -> None:
    """Một instance PrismLauncher trong hộp cát Flatpak — đúng cách cài trên máy chủ dự án."""
    inst = home / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances" / name
    (inst / ".minecraft").mkdir(parents=True)
    (inst / "instance.cfg").write_text(f"name={name}\n", encoding="utf-8")
    (inst / "mmc-pack.json").write_text(
        json.dumps(
            {
                "components": [
                    {"uid": "net.minecraft", "version": game_version},
                    {"uid": "net.fabricmc.fabric-loader", "version": "0.15.0"},
                ]
            }
        ),
        encoding="utf-8",
    )


def test_flatpak_instances_show_up_in_the_import_dialog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Quét xong, danh sách trong hộp thoại phải có đúng bản chơi cài bằng Flatpak."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _make_flatpak_prism_instance(fake_home, "RLCraft", "1.12.2")
    monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
    monkeypatch.setenv("HOME", str(fake_home))

    view, _bridge = build_view(make_launcher(tmp_path / "data"))
    root_item = view.rootObject()
    assert root_item is not None

    import_bridge = view.rootContext().contextProperty("importBridge")
    import_bridge.scanLaunchers()

    wait_until(lambda: bool(import_bridge.property("scanResults")))
    results = import_bridge.property("scanResults")

    assert [found["instanceName"] for found in results] == ["RLCraft"]
    assert results[0]["launcher"] == "PrismLauncher"
    assert results[0]["gameVersion"] == "1.12.2"
    assert results[0]["loaderKind"] == "fabric"
