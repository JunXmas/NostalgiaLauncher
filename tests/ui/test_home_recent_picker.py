"""Trang chủ mặc định mở bản chơi gần nhất — không phải mục đầu bảng chữ cái.

Tách khỏi test_qml.py: cùng dựng home + picker qua build_home(), nhóm hành vi
"chọn mặc định theo lastPlayedAt" riêng biệt khỏi test nạp/điều hướng QML chung.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication

from nostalgia.instance.model import Instance
from nostalgia.ui.app import build_view
from test_qml import make_launcher

pytestmark = pytest.mark.usefixtures("qt_app")


def build_home(tmp_path: Path, played_at: dict[str, int]) -> tuple[object, object]:
    """Ba bản chơi tên theo thứ tự chữ cái, mốc chơi cuối do test đặt (0 = chưa chơi)."""
    from PySide6.QtCore import QObject

    launcher = make_launcher(tmp_path)
    for instance_id, last_played_at in played_at.items():
        launcher.create_instance(Instance(instance_id=instance_id, version_id="1.20.1"))
        if last_played_at:
            launcher.record_play_session(instance_id, last_played_at - 60, last_played_at)
    view, _bridge = build_view(launcher)
    QGuiApplication.processEvents()
    root_item = view.rootObject()
    assert root_item is not None
    home = root_item.findChild(QObject, "homePage")
    picker = root_item.findChild(QObject, "homeInstancePicker")
    assert home is not None and picker is not None
    return home, picker


def picker_rows(picker: object) -> list[str]:
    """`model` là mảng JS: PySide trả `QJSValue`, phải đổi sang Python mới đọc được."""
    rows = picker.property("model")
    return list(rows.toVariant() if hasattr(rows, "toVariant") else rows)


def test_the_picker_opens_on_the_instance_played_most_recently(tmp_path: Path) -> None:
    """Mặc định cũ là mục đầu bảng chữ cái, nên người dùng bấm CHƠI là chạy nhầm bản. Giờ
    mặc định phải là bản vừa chơi — kiểm qua `instanceId`, không qua chỉ số, để test không
    đổi nghĩa nếu thứ tự danh sách đổi."""
    home, _picker = build_home(
        tmp_path, {"a-dau-bang": 1_700_000_000, "b-giua": 1_700_003_000, "c-cuoi": 1_700_001_000}
    )

    assert home.property("chosen")["instanceId"] == "b-giua"


def test_a_brand_new_machine_still_opens_on_the_first_instance(tmp_path: Path) -> None:
    """Chưa chơi lần nào thì mọi `lastPlayedAt` đều 0: phải giữ mục đầu, không được để trống."""
    home, _picker = build_home(tmp_path, {"a-dau-bang": 0, "b-giua": 0, "c-cuoi": 0})

    assert home.property("chosen")["instanceId"] == "a-dau-bang"


def test_picking_by_hand_still_wins_over_the_default(tmp_path: Path) -> None:
    """Mặc định là một binding; gán tay phải phá được nó, nếu không người dùng chọn xong lại
    bị kéo về bản vừa chơi."""
    home, _picker = build_home(
        tmp_path, {"a-dau-bang": 1_700_000_000, "b-giua": 1_700_003_000, "c-cuoi": 0}
    )
    home.setProperty("chosenIndex", 2)
    QGuiApplication.processEvents()

    assert home.property("chosen")["instanceId"] == "c-cuoi"


def test_the_closed_picker_says_how_many_instances_there_are(tmp_path: Path) -> None:
    """Hộp đóng chỉ hiện một dòng, nên không có viên đếm là người dùng tưởng chỉ có một bản."""
    _home, picker = build_home(tmp_path, {"a-dau-bang": 0, "b-giua": 0, "c-cuoi": 0})

    assert picker.property("badge") == "3 bản"


def test_a_single_instance_gets_no_count_badge(tmp_path: Path) -> None:
    """ "1 bản" là nhiễu: chỉ đếm khi thật sự có nhiều hơn một."""
    _home, picker = build_home(tmp_path, {"a-dau-bang": 0})

    assert picker.property("badge") == ""


def test_the_open_list_puts_the_recent_instance_first_and_labels_it(tmp_path: Path) -> None:
    """Mở khay ra phải nhận ra ngay bản vừa chơi: nó đứng đầu và được đánh dấu "vừa chơi"."""
    _home, picker = build_home(
        tmp_path, {"a-dau-bang": 1_700_000_000, "b-giua": 1_700_003_000, "c-cuoi": 0}
    )
    rows = picker_rows(picker)

    assert rows[0].startswith("b-giua"), "bản vừa chơi phải đứng đầu khay"
    assert [row.split("  ")[0] for row in rows] == ["b-giua", "a-dau-bang", "c-cuoi"]
    # Nhãn là một Text riêng chứ không nối vào chuỗi hàng: tên dài bị elide sẽ nuốt mất nhãn.
    assert picker.property("markedIndex") == 0, "hàng vừa chơi phải được đánh dấu"
    assert picker.property("markLabel") == "vừa chơi"
    assert picker.property("currentIndex") == 0, "hàng sáng phải là hàng của bản đang chọn"


def test_nothing_is_labelled_recent_when_nothing_was_ever_played(tmp_path: Path) -> None:
    """Máy mới: không bản nào được gắn "vừa chơi", và thứ tự giữ nguyên bảng chữ cái."""
    _home, picker = build_home(tmp_path, {"a-dau-bang": 0, "b-giua": 0, "c-cuoi": 0})
    rows = picker_rows(picker)

    assert picker.property("markedIndex") == -1, "chưa chơi gì thì không hàng nào là vừa chơi"
    assert [row.split("  ")[0] for row in rows] == ["a-dau-bang", "b-giua", "c-cuoi"]

