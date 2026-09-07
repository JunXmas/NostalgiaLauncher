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
        for page_index in range(6):
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
    assert targets == [1, 2, 2, 3, 4, 5], "sáu thẻ phải dẫn tới năm trang thật của thanh bên"
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


def test_room_code_boxes_advance_split_paste_and_backspace(tmp_path: Path) -> None:
    """Mã phòng nhập qua ba ô x 6: gõ liền 18 ký tự thường tự nhảy ô và viết hoa; dán chuỗi có
    gạch tự chia; Backspace ở ô rỗng lùi về ô trước. Nút Vào phòng chỉ sáng khi đủ 18."""
    from PySide6.QtCore import QObject, Qt
    from PySide6.QtTest import QTest

    view, _bridge = build_view(make_launcher(tmp_path))
    view.show()
    QGuiApplication.processEvents()
    root_item = view.rootObject()
    assert root_item is not None
    root_item.findChild(QObject, "sidebar").setProperty("currentIndex", 4)
    for _ in range(50):
        QGuiApplication.processEvents()
        code_field = root_item.findChild(QObject, "roomCodeField")
        if code_field is not None:
            break
    assert code_field is not None
    boxes = [root_item.findChild(QObject, f"roomCodeBox{i}") for i in range(3)]
    join_button = root_item.findChild(QObject, "joinButton")
    assert join_button is not None and join_button.property("clickable") is False

    boxes[0].focusInput()
    for character in "k7mpx3q9zvr2tb5hnw":  # QTest.keyClicks chỉ nhận QWidget, không nhận QWindow
        QTest.keyClick(view, character)
    QGuiApplication.processEvents()
    assert [b.property("text") for b in boxes] == ["K7MPX3", "Q9ZVR2", "TB5HNW"]
    assert code_field.property("code") == "K7MPX3Q9ZVR2TB5HNW"
    assert code_field.property("complete") is True and join_button.property("clickable") is True

    code_field.clear()
    QGuiApplication.processEvents()
    assert code_field.property("code") == ""
    code_field.setCode(" abcdef-ghjkmn pqrstu ")
    QGuiApplication.processEvents()
    assert [b.property("text") for b in boxes] == ["ABCDEF", "GHJKMN", "PQRSTU"]

    boxes[2].setProperty("text", "")
    boxes[2].focusInput()
    QTest.keyClick(view, Qt.Key.Key_Backspace)
    QGuiApplication.processEvents()
    assert boxes[1].property("text") == "GHJKM" and boxes[1].property("focused") is True
