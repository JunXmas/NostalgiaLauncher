"""Toggle và Slider kiểu Bedrock: dựng thật, gọi thật, đọc lại hình khối.

Vì sao đáng có: hai widget này là hình, mà hình thì test dễ dừng ở "nạp được" rồi bỏ qua
việc núm trượt sai bên hay giá trị kéo ra ngoài khoảng. Ở đây kiểm đúng hai thứ đó, cộng
với API mà bốn chỗ gọi trong SettingsPage phụ thuộc vào.

Tín hiệu QML không lộ ra thành thuộc tính Python trên `QObject` trần, nên mỗi phép thử ghi
kết quả vào một thuộc tính khai ngay trong đoạn QML rồi đọc lại — đúng đường mà QML đi.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Q_ARG, QEventLoop, QMetaObject, QObject, Qt, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

pytestmark = pytest.mark.usefixtures("qt_app")

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "nostalgia" / "ui" / "qml"

# Engine hoặc component chết thì cả cây QML chúng dựng chết theo, và test đỏ vì "Internal
# C++ object already deleted" chứ không vì widget sai. Giữ cả ba sống tới hết phiên.
LIVE_OBJECTS: list[object] = []


def build(source: str) -> QObject:
    """Dựng một đoạn QML trong thư mục qml thật, và coi MỌI lỗi là hỏng."""
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    qml_component = QQmlComponent(engine)
    qml_component.setData(source.encode("utf-8"), QUrl.fromLocalFile(str(QML_DIR / "probe.qml")))
    scene = qml_component.create()
    assert not qml_component.errors(), [e.toString() for e in qml_component.errors()]
    assert scene is not None
    QQmlEngine.setObjectOwnership(scene, QQmlEngine.CppOwnership)  # type: ignore[attr-defined]
    LIVE_OBJECTS.extend((engine, qml_component, scene))
    return scene


def find(scene: QObject, name: str) -> QObject:
    found = scene.findChild(QObject, name)
    assert found is not None, f"không thấy phần tử {name!r}"
    return found


def call(widget: QObject, method: str, argument: float) -> None:
    assert QMetaObject.invokeMethod(
        widget,
        method,
        Qt.DirectConnection,  # type: ignore[attr-defined]
        Q_ARG("QVariant", argument),
    ), f"không gọi được {method}()"


def test_toggle_keeps_the_api_the_settings_page_calls() -> None:
    """`checked` + `toggled(bool)` là hợp đồng với SettingsPage.qml:101,117,134,150.
    Đổi kiểu vẽ được, đổi hợp đồng thì bốn chỗ đó câm lặng."""
    scene = build(
        "import QtQuick\n"
        'Item { property string heard: ""\n'
        '  Toggle { objectName: "probe"; checked: false\n'
        '    onToggled: function (checked) { parent.heard += String(checked) + ";" } } }'
    )
    toggle = find(scene, "probe")

    assert toggle.property("checked") is False
    toggle.toggled.emit(True)  # type: ignore[attr-defined]
    QGuiApplication.processEvents()

    assert scene.property("heard") == "true;", "tín hiệu toggled(bool) phải còn nguyên chữ ký"


def test_toggle_is_a_square_block_not_a_pill() -> None:
    """Ảnh mẫu là ô vuông góc nhọn. Một `radius` lén vào là trôi ngược về kiểu iOS cũ."""
    toggle = find(build('import QtQuick\nItem { Toggle { objectName: "probe" } }'), "probe")

    assert (toggle.property("width"), toggle.property("height")) == (44, 24)
    radii = [child.property("radius") for child in toggle.findChildren(QObject)]
    assert all(radius in (None, 0) for radius in radii), f"khối Bedrock không bo góc: {radii}"


def test_the_toggle_knob_and_mark_swap_sides_when_it_flips() -> None:
    """Bật thì núm sang phải và ký hiệu là `I`; tắt thì ngược lại. Núm đứng yên = công tắc
    không nói được trạng thái của chính nó."""
    scene = build('import QtQuick\nItem { Toggle { objectName: "probe"; checked: false } }')
    toggle = find(scene, "probe")
    knob, mark = find(toggle, "toggleKnob"), find(toggle, "toggleMark")
    QGuiApplication.processEvents()

    assert knob.property("x") == 0
    assert mark.property("text") == "O"
    assert mark.property("x") > 0, "ký hiệu nằm ở nửa KHÔNG có núm"

    toggle.setProperty("checked", True)
    QGuiApplication.processEvents()

    assert mark.property("text") == "I"
    assert mark.property("x") == 0


def test_the_slider_reports_the_value_it_was_moved_to() -> None:
    """Kéo tới giữa quãng chạy phải ra giữa khoảng giá trị, và phải phát `moved`."""
    scene = build(
        "import QtQuick\n"
        "Item { property real lastMoved: -1\n"
        '  Slider { objectName: "probe"; from: 0; to: 100; value: 0; width: 204\n'
        "    onMoved: function (value) { parent.lastMoved = value } } }"
    )
    slider = find(scene, "probe")

    # Đúng giữa quãng chạy của núm: nửa quãng cộng nửa bề ngang núm.
    call(slider, "moveTo", slider.property("travel") / 2 + slider.property("knobWidth") / 2)

    assert scene.property("lastMoved") == pytest.approx(50.0)
    assert slider.property("value") == pytest.approx(50.0)


def test_the_slider_clamps_instead_of_flinging_the_knob_off_the_track() -> None:
    """Giá trị ngoài khoảng đến từ dữ liệu thật (RAM đã lưu lớn hơn `to` mới). Núm phải
    dừng ở mép, không bay ra khỏi rãnh."""
    slider = find(
        build(
            'import QtQuick\nItem { Slider { objectName: "probe"; from: 1; to: 8; '
            "value: 99; width: 204 } }"
        ),
        "probe",
    )

    assert slider.property("fraction") == 1.0
    call(slider, "moveTo", -500.0)
    assert slider.property("value") == pytest.approx(1.0)
    call(slider, "moveTo", 5000.0)
    assert slider.property("value") == pytest.approx(8.0)


def test_a_zero_width_range_does_not_divide_by_zero() -> None:
    """`from == to` xảy ra khi danh sách lựa chọn co lại còn một. NaN ở đây làm núm biến mất."""
    slider = find(
        build(
            'import QtQuick\nItem { Slider { objectName: "probe"; from: 4; to: 4; '
            "value: 4; width: 204 } }"
        ),
        "probe",
    )

    assert slider.property("fraction") == 0
    call(slider, "moveTo", 120.0)
    assert slider.property("value") == pytest.approx(4.0)


def run_animation(milliseconds: int) -> None:
    """Chạy vòng lặp sự kiện thật `milliseconds` ms.

    Hoạt ảnh chỉ tồn tại giữa hai khung hình; `processEvents()` một lần không thấy gì.
    Đoạn QML tự ghi lại đỉnh/đáy trong lúc chạy — không phải đoán đúng thời điểm chụp.
    """
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def test_the_check_tick_springs_past_full_size_before_settling() -> None:
    """Dấu tick phải NHẢY RA: phóng quá cỡ rồi co về 1.

    Chỉ kiểm "cuối cùng bằng 1" thì một phép gán thẳng `scale: 1` cũng xanh, mà như thế là
    tick hiện đột ngột — đúng thứ cần tránh. Nên gác ở chỗ đỉnh vượt 1.
    """
    scene = build(
        "import QtQuick\n"
        "Item { property real peak: 0\n"
        '  CheckRow { id: row; objectName: "probe"; label: "x"; checked: false }\n'
        '  Binding { target: parent; property: "ignored"; value: 0 }\n'
        "  Timer { interval: 8; repeat: true; running: true\n"
        "    onTriggered: { if (row.tickScale > parent.peak) parent.peak = row.tickScale } } }"
    )
    row = find(scene, "probe")
    tick = find(row, "checkTick")
    assert tick.property("scale") == 0, "chưa tick thì dấu tick không được hiện"

    row.setProperty("checked", True)
    run_animation(400)
    peak = float(scene.property("peak"))

    assert peak > 1.08, f"dấu tick KHÔNG nảy ra (đỉnh chỉ {peak:.3f}, chờ vượt 1)"
    assert tick.property("scale") == pytest.approx(1.0, abs=0.01), "nảy xong phải về đúng cỡ"


def test_unticking_shrinks_away_without_bouncing() -> None:
    """Nảy lúc BIẾN MẤT trông như lỗi vẽ. Chiều tắt phải co thẳng.

    Gác ở cỡ ÂM chứ không ở cỡ vượt 1: một `OutBack` đặt nhầm cho chiều tắt sẽ vọt
    xuống **dưới** 0 (dấu tick lộn ngược một nhịp) chứ không vọt lên trên 1.
    """
    scene = build(
        "import QtQuick\n"
        "Item { property real dip: 1\n"
        '  CheckRow { id: row; objectName: "probe"; label: "x"; checked: true }\n'
        "  Timer { interval: 8; repeat: true; running: true\n"
        "    onTriggered: { if (row.tickScale < parent.dip) parent.dip = row.tickScale } } }"
    )
    row = find(scene, "probe")
    run_animation(250)          # để nó lên tới 1 trước
    scene.setProperty("dip", 1.0)
    row.setProperty("checked", False)
    run_animation(300)
    dip = float(scene.property("dip"))

    assert dip >= -0.005, f"dấu tick NẢY NGƯỢC lúc biến mất (xuống tới {dip:.3f})"
    assert find(row, "checkTick").property("scale") == pytest.approx(0.0, abs=0.01)


def test_the_dropdown_tray_overshoots_then_settles_into_place() -> None:
    """Khay phải trượt QUÁ đà rồi khựng về đúng bố cục.

    Chỉ kiểm chiều cao cuối cùng thì một `NumberAnimation` phẳng lì cũng xanh — mà đó
    chính là cái trượt đều đều cần thay. Nên gác ở chỗ vượt chiều cao đích.
    """
    scene = build(
        "import QtQuick\n"
        "Item { property real peak: 0\n"
        '  Dropdown { id: drop; objectName: "probe"; model: ["a", "b", "c"] }\n'
        "  Timer { interval: 8; repeat: true; running: true\n"
        "    onTriggered: { if (drop.trayHeight > parent.peak) parent.peak = drop.trayHeight } } }"
    )
    drop = find(scene, "probe")
    settled = 3 * 32 + 8

    drop.setProperty("open", True)
    run_animation(500)
    peak = float(scene.property("peak"))

    assert peak > settled + 4, f"khay KHÔNG vọt quá đà (đỉnh {peak}, đích {settled})"
    assert drop.property("trayHeight") == pytest.approx(settled), "vọt xong phải về đúng bố cục"


def test_closing_the_dropdown_does_not_bounce_below_zero() -> None:
    """Chiều đóng vọt xuống dưới 0 bị Qt kẹp lại, thành một nhịp khay đứng hình."""
    scene = build(
        "import QtQuick\n"
        "Item { property real dip: 9999\n"
        '  Dropdown { id: drop; objectName: "probe"; model: ["a", "b", "c"]; open: true }\n'
        "  Timer { interval: 8; repeat: true; running: true\n"
        "    onTriggered: { if (drop.trayHeight < parent.dip) parent.dip = drop.trayHeight } } }"
    )
    drop = find(scene, "probe")
    run_animation(500)
    scene.setProperty("dip", 9999.0)

    drop.setProperty("open", False)
    run_animation(400)

    assert float(scene.property("dip")) >= -0.01, "khay nảy ngược xuống dưới 0 khi đóng"
    assert drop.property("trayHeight") == pytest.approx(0.0, abs=0.01)
