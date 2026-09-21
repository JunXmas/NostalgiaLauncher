"""Giao diện QML: nạp sạch, không cảnh báo, và cầu nối đưa đúng dữ liệu thật sang.

Vì sao đáng có: một lỗi đánh máy trong QML **không làm chương trình chết** — nó chỉ làm một
binding im lặng trả về `undefined`, và người dùng thấy một ô trống mà không hiểu vì sao. Test
ở đây biến loại lỗi đó thành CI đỏ.

Chạy hoàn toàn không cần màn hình (`QT_QPA_PLATFORM=offscreen`), nên chạy được trên máy chủ CI.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView

from nostalgia.api import Launcher
from nostalgia.instance.model import Instance
from nostalgia.ui.app import build_view

pytestmark = pytest.mark.usefixtures("qt_app")


def make_launcher(tmp_path: Path) -> Launcher:
    return Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")


def test_the_interface_loads_without_a_single_qml_error(tmp_path: Path) -> None:
    """Không lỗi nạp, và cũng KHÔNG một cảnh báo lúc chạy.

    `view.errors()` chỉ thấy lỗi cú pháp. Một trang thiếu `import "../"` vẫn nạp được, rồi
    kêu `ReferenceError: Theme is not defined` khi dựng — đó là cảnh báo, phải hứng riêng.
    """
    from PySide6.QtCore import QObject, qInstallMessageHandler

    warnings: list[str] = []
    qInstallMessageHandler(lambda _kind, _context, message: warnings.append(message))
    try:
        view, _bridge = build_view(make_launcher(tmp_path))
        QGuiApplication.processEvents()
        # Các trang nạp lười, nên phải ghé qua từng trang thì lỗi của trang đó mới lộ.
        root_item = view.rootObject()
        assert root_item is not None
        sidebar = root_item.findChild(QObject, "sidebar")
        assert sidebar is not None
        for page_index in range(7):
            sidebar.setProperty("currentIndex", page_index)
            QGuiApplication.processEvents()
        sidebar.setProperty("currentIndex", 0)
    finally:
        qInstallMessageHandler(None)

    assert view.status() == QQuickView.Status.Ready
    assert [error.toString() for error in view.errors()] == []
    assert view.rootObject() is not None
    assert warnings == []


def test_the_interface_renders_to_an_image(qt_app: QGuiApplication, tmp_path: Path) -> None:
    """Nạp được chưa chắc vẽ được. Vẽ ra ảnh mới là bằng chứng."""
    view, _bridge = build_view(make_launcher(tmp_path))
    view.show()
    qt_app.processEvents()

    image = view.grabWindow()

    assert not image.isNull()
    assert image.width() > 800
    assert image.height() > 500


def test_the_bridge_hands_qml_the_real_instances(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    launcher.create_instance(Instance(instance_id="vui-ve", version_id="1.20.1"))
    _view, bridge = build_view(launcher)

    [row] = bridge.instances
    assert (row["instanceId"], row["label"], row["versionId"]) == ("vui-ve", "vui-ve", "1.20.1")
    assert row["gameDir"].endswith("instances/vui-ve")


def test_the_bridge_hands_qml_the_real_accounts(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    launcher.add_offline_account("Jun")
    _view, bridge = build_view(launcher)

    accounts = bridge.accounts

    assert [account["playerName"] for account in accounts] == ["Jun"]
    assert accounts[0]["accountKind"] == "offline"
    assert "access_token" not in accounts[0], "vé đăng nhập không được lọt sang tầng vẽ"
    assert "refreshToken" not in accounts[0]


def test_nothing_is_busy_before_anything_starts(tmp_path: Path) -> None:
    _view, bridge = build_view(make_launcher(tmp_path))

    assert bridge.busy is False
    assert bridge.progressFraction == 0.0


def find_hero_cards(view: QQuickView) -> list[object]:
    from PySide6.QtCore import QObject

    root_item = view.rootObject()
    assert root_item is not None
    return list(root_item.findChildren(QObject, "heroCard"))


def test_every_card_on_the_hero_points_at_a_real_page(tmp_path: Path) -> None:
    """Các thẻ nổi phải bấm được thật, và mỗi thẻ phải dẫn tới ĐÚNG trang của nó.

    Chỉ kiểm "bấm xong có gì đó xảy ra" là chưa đủ: một thẻ dẫn nhầm trang vẫn qua được kiểu
    kiểm đó. Ở đây đọc thẳng đích của từng thẻ.
    """
    view, _bridge = build_view(make_launcher(tmp_path))
    cards = find_hero_cards(view)

    assert len(cards) == 6, "bản mẫu có sáu thẻ nổi"
    targets = sorted(card.property("pageIndex") for card in cards)
    # Thư viện gộp mod + shader + gói tài nguyên, nên hai thẻ MOD và TÀI NGUYÊN cùng mở
    # trang 2; thẻ TÀI NGUYÊN mở sẵn chip Gói tài nguyên.
    assert targets == [1, 2, 2, 3, 4, 6], "sáu thẻ phải dẫn tới năm trang thật của thanh bên"
    assert all(card.property("title") for card in cards), "thẻ nào cũng phải có nhãn"


def test_activating_a_card_actually_changes_the_page(tmp_path: Path) -> None:
    """Bấm thẻ phải đổi trang y như bấm ở thanh bên — nếu không thì nó chỉ là hình trang trí."""
    from PySide6.QtCore import QObject

    view, _bridge = build_view(make_launcher(tmp_path))
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None, "không tìm thấy thanh bên"

    cards = find_hero_cards(view)
    multiplayer = next(card for card in cards if card.property("title") == "CHƠI CHUNG")
    multiplayer.activated.emit()

    assert sidebar.property("currentIndex") == 4


def test_hero_cards_sit_inside_the_photo_and_never_overlap(tmp_path: Path) -> None:
    """Mỗi thẻ neo vào một công trình trong ảnh, nên toạ độ neo phải nằm trong ảnh, và hai
    thẻ không được đè lên nhau — đè là mất chữ, mà chỉ soi mắt mới thấy. Test này thay mắt.
    """
    view, _bridge = build_view(make_launcher(tmp_path))
    cards = find_hero_cards(view)
    rectangles: list[tuple[float, float, float, float]] = []
    for card in cards:
        assert 0.0 < card.property("landmarkX") < 1.0
        assert 0.0 < card.property("landmarkY") < 1.0
        # Chỉ so phần thân thẻ: que nối được phép chạy qua khoảng trống giữa các thẻ.
        left = card.property("x")
        top = card.property("y") + (card.property("stemLength") if card.property("below") else 0)
        rectangles.append(
            (left, top, left + card.property("width"), top + card.property("cardHeight"))
        )

    for index, first in enumerate(rectangles):
        for second in rectangles[index + 1 :]:
            separated = (
                first[2] <= second[0]
                or second[2] <= first[0]
                or first[3] <= second[1]
                or second[3] <= first[1]
            )
            assert separated, f"hai thẻ nổi đè nhau: {first} và {second}"


def test_clicking_a_loader_button_keeps_the_create_dialog_open(tmp_path: Path) -> None:
    """Lỗi thật đã gặp: bấm nút loader trong hộp tạo bản chơi thì hộp đóng luôn, vì TapHandler
    không nuốt sự kiện và cú bấm lọt xuống màn tối "bấm ra ngoài thì đóng". Bấm chuột thật."""
    from PySide6.QtCore import QObject, QPointF, Qt
    from PySide6.QtTest import QTest

    view, _bridge = build_view(make_launcher(tmp_path))
    view.show()
    QGuiApplication.processEvents()
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", 1)
    for _ in range(50):  # Loader nạp trang xong mới có hộp thoại
        QGuiApplication.processEvents()
        dialog = root_item.findChild(QObject, "createDialog")
        if dialog is not None:
            break
    assert dialog is not None
    dialog.openDialog()
    QGuiApplication.processEvents()
    assert dialog.property("visible") is True

    loader_row = root_item.findChild(QObject, "loaderRow")
    assert loader_row is not None
    fabric_button = loader_row.childItems()[1]  # Vanilla, Fabric, Forge, NeoForge
    center = fabric_button.mapToScene(
        QPointF(fabric_button.property("width") / 2, fabric_button.property("height") / 2)
    )
    QTest.mouseClick(
        view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center.toPoint()
    )
    QGuiApplication.processEvents()

    assert dialog.property("loaderKind") == "fabric", "nút loader phải nhận được cú bấm"
    assert dialog.property("visible") is True, "hộp không được đóng khi bấm bên trong"

    # Bấm ra màn tối bên ngoài hộp thì mới đóng.
    QTest.mouseClick(
        view,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPointF(view.width() - 5, 5).toPoint(),
    )
    QGuiApplication.processEvents()
    assert dialog.property("visible") is False


def test_create_button_explains_what_is_missing_and_name_is_optional(tmp_path: Path) -> None:
    """Người dùng bấm "Tạo" mà không thấy gì xảy ra là vì nút bị mờ không lý do. Giờ nút mờ
    phải nói rõ còn thiếu bước nào, và tên để trống thì tự đặt theo loader + phiên bản."""
    from PySide6.QtCore import QObject

    view, _bridge = build_view(make_launcher(tmp_path))
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", 1)
    for _ in range(50):
        QGuiApplication.processEvents()
        dialog = root_item.findChild(QObject, "createDialog")
        if dialog is not None:
            break
    assert dialog is not None

    assert dialog.property("canCreate") is False
    assert "phiên bản Minecraft" in dialog.property("missingStep")

    dialog.setProperty("loaderKind", "forge")
    dialog.setProperty("gameVersion", "1.20.1")
    QGuiApplication.processEvents()
    assert "Forge" in dialog.property("missingStep"), "Forge còn cần chọn bản loader"
    assert dialog.property("defaultName") == "Forge 1.20.1"

    dialog.setProperty("loaderVersion", "1.20.1-47.4.10")
    QGuiApplication.processEvents()
    assert dialog.property("missingStep") == ""
    assert dialog.property("canCreate") is True


def test_the_resources_card_opens_the_library_on_resource_packs(tmp_path: Path) -> None:
    """Gộp trang TÀI NGUYÊN vào Thư viện không được làm mất lối tắt: thẻ trên hero mở Thư viện
    với chip Gói tài nguyên chọn sẵn."""
    from PySide6.QtCore import QObject

    view, _bridge = build_view(make_launcher(tmp_path))
    root_item = view.rootObject()
    assert root_item is not None
    resources = next(
        card for card in find_hero_cards(view) if card.property("title") == "TÀI NGUYÊN"
    )
    resources.activated.emit()
    for _ in range(50):
        QGuiApplication.processEvents()
        library = root_item.findChild(QObject, "contentPage")
        if library is not None and library.property("kind") == "resourcepack":
            break
    assert library is not None
    assert library.property("kind") == "resourcepack"
    assert root_item.property("libraryKind") == "", "dùng xong phải xoá để lần sau mở bình thường"


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


def test_bench_scripts_build_a_qapplication_not_a_qguiapplication() -> None:
    """`build_view()` tạo `QSystemTrayIcon` — widget, đòi `QApplication`. Bench nào dựng
    `QGuiApplication` sẽ chết ở `QWidget: Cannot create a QWidget without QApplication`, mà
    không test nào bắt được vì test dùng đúng lớp (`tests/conftest.py`). Kiểm tĩnh, vì không
    thể dựng hai QApplication trong cùng một phiên để thử thật."""
    bench_dir = Path(__file__).resolve().parents[2] / "bench"
    scripts = sorted(bench_dir.glob("ui_*.py"))
    assert scripts, f"không thấy bench giao diện nào trong {bench_dir}"
    offenders = [p.name for p in scripts if "QGuiApplication(" in p.read_text(encoding="utf-8")]
    assert not offenders, f"bench dựng QGuiApplication, chết khi build_view tạo tray: {offenders}"
