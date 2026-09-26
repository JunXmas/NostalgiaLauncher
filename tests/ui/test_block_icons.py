"""Icon khối xoay ở thanh bên: dải sprite sinh ra sao, và nó xoay/hãm/quay về thế nào.

Ba thứ đáng gác, vì mỗi thứ đã từng sai ở bản mẫu:
- Khối bị lộn ngược khi đảo dấu phép cull mặt khuất — kiểm bằng "mặt trên phải SÁNG hơn".
- Rời chuột thì nhảy cóc về khung 0 thay vì quay ngược — kiểm bằng "có ghé khung giữa".
- Rung đều tay thay vì kiểu trứng-sắp-nở — kiểm bằng "phải có cả pha giật lẫn pha lặng".
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QObject, QTimer, QUrl
from PySide6.QtGui import QColor, QImage, qGray
from PySide6.QtQml import QQmlComponent, QQmlEngine

from nostalgia.storage.paths import DataPaths
from nostalgia.ui import blocks
from nostalgia.ui.block_bridge import newest_client_jar
from nostalgia.ui.block_textures import BLOCK_TEXTURES, fallback_faces

pytestmark = pytest.mark.usefixtures("qt_app")

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "nostalgia" / "ui" / "qml"
LIVE_OBJECTS: list[object] = []


class FakeIcons(QObject):
    """Đứng thay `blockIcons` thật: QML chỉ cần ba thứ này, không cần sinh ảnh."""

    def __init__(self, strips: dict[str, str]) -> None:
        super().__init__()
        self._strips = strips

    from PySide6.QtCore import Property

    @Property("QVariant", constant=True)  # type: ignore[arg-type]
    def strips(self) -> dict[str, str]:
        return self._strips

    @Property(int, constant=True)
    def frameCount(self) -> int:
        return blocks.FRAME_COUNT

    @Property(int, constant=True)
    def frameSize(self) -> int:
        return blocks.FRAME_SIZE


def build(source: str, strips: dict[str, str] | None = None) -> QObject:
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    icons = FakeIcons(strips or {})
    engine.rootContext().setContextProperty("blockIcons", icons)
    qml_component = QQmlComponent(engine)
    qml_component.setData(source.encode("utf-8"), QUrl.fromLocalFile(str(QML_DIR / "probe.qml")))
    scene = qml_component.create()
    assert not qml_component.errors(), [e.toString() for e in qml_component.errors()]
    assert scene is not None
    QQmlEngine.setObjectOwnership(scene, QQmlEngine.CppOwnership)  # type: ignore[attr-defined]
    LIVE_OBJECTS.extend((engine, qml_component, icons, scene))
    return scene


def run_animation(milliseconds: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def test_the_rendered_cube_is_not_upside_down() -> None:
    """Mặt trên phải sáng hơn mặt dưới cùng của khối.

    Phép cull mặt khuất dựa vào DẤU của tích có hướng 2D, mà trục y màn hình hướng xuống.
    Đảo dấu thì khối vẫn vẽ ra một hình lập phương trông hợp lý — chỉ là lộn ngược, và
    mắt người soi ảnh tĩnh rất dễ bỏ qua. Ở đây so độ sáng nên đảo dấu là đỏ ngay.
    """
    frame = blocks.render_frame(fallback_faces("grass"), blocks.START_DEGREES, 64)

    def brightness(y: int) -> float:
        row = [frame.pixelColor(x, y) for x in range(64)]
        lit = [qGray(colour.rgb()) for colour in row if colour.alpha() > 200]
        assert lit, f"hàng y={y} rỗng — khối không lấp đầy khung"
        return sum(lit) / len(lit)

    # y=8 nằm hẳn trong mặt trên, y=48 hẳn trong hai mặt bên. Tránh dải y≈15..25 vì ở đó
    # mặt trên và mặt bên trộn nhau trong cùng một hàng, trung bình ra vô nghĩa.
    top, bottom = brightness(8), brightness(48)
    assert top > bottom + 15, f"khối LỘN NGƯỢC (trên {top:.0f} không sáng hơn dưới {bottom:.0f})"


def test_the_strip_holds_one_full_turn_of_distinct_frames() -> None:
    """Dải phải đủ `FRAME_COUNT` khung KHÁC nhau. Quên nhân góc theo chỉ số thì mọi khung
    giống hệt nhau, ảnh vẫn ra đúng kích thước và không có lỗi nào nổi lên."""
    strip = blocks.render_strip(fallback_faces("diamond"))
    assert strip.width() == blocks.FRAME_SIZE * blocks.FRAME_COUNT
    size = blocks.FRAME_SIZE
    first = strip.copy(0, 0, size, size)
    quarter = strip.copy(size * (blocks.FRAME_COUNT // 4), 0, size, size)
    assert first != quarter, "mọi khung giống nhau — khối không xoay"


def test_strips_come_from_the_jar_when_one_is_present(tmp_path: Path) -> None:
    """Có jar thì tên file phải mang dấu `_jar`, và texture phải là texture trong jar.

    Gác đúng chỗ đã từng hỏng: `ensure_strips` bỏ qua file có sẵn, nên nếu đặt tên không
    phân biệt nguồn thì ảnh vẽ-bằng-code sẽ đóng băng vĩnh viễn kể cả sau khi cài game.
    """
    jar = tmp_path / "client.jar"
    plate = QImage(16, 16, QImage.Format.Format_ARGB32)
    plate.fill(QColor(0xFF, 0x00, 0xFF))  # hồng cánh sen: không màu dự phòng nào giống
    # Stub PySide6 khai `format: bytes`, nhưng runtime chỉ nhận `str` — đưa bytes vào
    # là ValueError. Tin runtime, không tin stub.
    plate.save(str(tmp_path / "t.png"), "PNG")  # type: ignore[call-overload]
    with zipfile.ZipFile(jar, "w") as archive:
        for name in ("grass_block_top", "grass_block_side"):
            archive.write(tmp_path / "t.png", f"assets/minecraft/textures/block/{name}.png")

    made = blocks.ensure_strips(tmp_path / "cache", jar)
    assert made["grass"].name.endswith("_jar.png"), "tên file phải phân biệt nguồn texture"
    strip = QImage(str(made["grass"]))
    centre = strip.pixelColor(blocks.FRAME_SIZE // 2, blocks.FRAME_SIZE // 2)
    assert centre.red() > 120 and centre.blue() > 120 and centre.green() < 90, (
        f"không dùng texture trong jar (màu giữa khung: {centre.name()})"
    )


def test_no_jar_still_yields_every_icon(tmp_path: Path) -> None:
    """Chưa cài bản chơi nào thì vẫn phải đủ icon — launcher mới cài là đúng cảnh này."""
    made = blocks.ensure_strips(tmp_path / "cache", None)
    assert set(made) == set(BLOCK_TEXTURES)
    assert all(path.name.endswith("_code.png") for path in made.values())


def test_newest_client_jar_picks_the_latest_install(tmp_path: Path) -> None:
    """Quét thư mục versions thật của người dùng: phải lấy bản mới nhất, và chịu được
    thư mục không có jar (bản chỉ có json — Fabric/Forge đặt kiểu đó)."""
    paths = DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")
    versions = paths.versions_dir
    for name, mtime in (("1.21", 1_000_000), ("26.3", 2_000_000)):
        (versions / name).mkdir(parents=True)
        jar = versions / name / f"{name}.jar"
        jar.write_bytes(b"x")
        os.utime(jar, (mtime, mtime))
    (versions / "fabric-loader-0.19-26.3").mkdir()  # chỉ có json, không jar

    assert newest_client_jar(versions) == versions / "26.3" / "26.3.jar"


def test_no_versions_directory_is_not_a_crash(tmp_path: Path) -> None:
    assert newest_client_jar(tmp_path / "khong-ton-tai") is None


def test_the_icon_falls_back_to_a_glyph_until_the_strip_exists() -> None:
    """Chưa sinh xong dải thì phải hiện chữ. Không có bước này thì thanh bên trống trơn
    trong suốt giây đầu mở launcher."""
    scene = build(
        'import QtQuick\nItem { BlockIcon { objectName: "probe"; block: "grass"; glyph: "⌂" } }'
    )
    icon = find(scene, "probe")
    assert icon.property("ready") is False
    assert icon.property("source") == ""


def test_hovering_spins_the_block_up_to_a_ceiling() -> None:
    """Tăng tốc dần rồi CHẠM TRẦN. Bỏ kẹp `vmax` thì khối quay loạn thành vệt mờ.

    Mẫu "sớm" bắt ở lần ĐẦU velocity vượt 0, không phải ở mốc đồng hồ cứng: máy CI bận
    thì 120 ms đầu animation chưa kịp tick một khung nào và mẫu đọc ra 0 — flaky."""
    scene = build(
        "import QtQuick\n"
        "Item { property real early: -1\n"
        '  BlockIcon { id: icon; objectName: "probe"; block: "grass"; spinning: true }\n'
        "  Timer { interval: 16; running: parent.early < 0; repeat: true\n"
        "          onTriggered: if (icon.velocity > 0 && icon.velocity < icon.vmax)"
        " parent.early = icon.velocity } }"
    )
    icon = find(scene, "probe")
    run_animation(2500)
    early = float(scene.property("early"))
    late = float(icon.property("velocity"))
    assert 0 < early < late, f"không tăng tốc dần (sớm {early:.3f}, muộn {late:.3f})"
    assert late == pytest.approx(icon.property("vmax"), abs=0.02), f"vượt trần: {late:.3f}"


def test_releasing_the_hover_rewinds_instead_of_snapping_home() -> None:
    """Rời chuột: hãm rồi QUAY NGƯỢC về khung 0, không nhảy cóc.

    Gác bằng "có ghé khung giữa chừng" chứ không bằng "cuối cùng về 0": nhảy cóc cũng về 0.

    Điều kiện đếm phải là `velocity === 0` — tức ĐÃ hãm xong, đang ở pha quay về. Đếm cả
    pha hãm thì test xanh kể cả khi pha quay về bị thay bằng `turn = 0`, vì lúc hãm khối
    vẫn đang trôi qua các khung giữa chừng. (Đã thử: bản gác sai không đỏ khi gỡ vá.)
    """
    scene = build(
        "import QtQuick\n"
        "Item { property int visits: 0\n"
        '  BlockIcon { id: icon; objectName: "probe"; block: "grass"; spinning: true }\n'
        "  Timer { interval: 16; repeat: true; running: true\n"
        "    onTriggered: if (!icon.spinning && icon.velocity === 0"
        " && icon.turn > 0.002 && icon.turn < 0.5) parent.visits++ } }"
    )
    icon = find(scene, "probe")
    run_animation(1500)
    icon.setProperty("spinning", False)
    run_animation(3000)

    assert int(scene.property("visits")) > 3, "NHẢY CÓC về 0 chứ không quay ngược"
    assert float(icon.property("turn")) == pytest.approx(0.0, abs=0.002), "phải dừng đúng khung 0"
    assert float(icon.property("velocity")) == 0


def test_the_shake_throbs_like_a_hatching_egg() -> None:
    """Chạm trần thì rung TỪNG CƠN: phải có cả nhịp giật lẫn pha lặng.

    Rung đều tay (bỏ bao hình sin^2) sẽ làm `lặng` bằng 0 và test này đỏ.
    """
    scene = build(
        "import QtQuick\n"
        "Item { property int go: 0; property int rest: 0\n"
        '  BlockIcon { id: icon; objectName: "probe"; block: "grass"; spinning: true }\n'
        "  Timer { interval: 16; repeat: true; running: true\n"
        "    onTriggered: { if (icon.velocity > icon.vmax * 0.95)"
        " { if (icon.amplitude > 0.001) parent.go++; else parent.rest++ } } } }"
    )
    run_animation(3500)
    go, rest = int(scene.property("go")), int(scene.property("rest"))
    assert go > 0, "KHÔNG RUNG khi đã chạm trần"
    assert rest > 0, f"RUNG ĐỀU chứ không theo nhịp (lặng={rest})"
    share = go / (go + rest)
    assert 0.25 < share < 0.55, f"NHỊP SAI: giật {share:.0%} thời gian, chờ ~40%"


def test_an_idle_icon_burns_no_frames() -> None:
    """Không rê chuột thì đồng hồ phải TẮT. Bảy icon quay không ở thanh bên là CPU quay
    suốt phiên dù chẳng ai nhìn."""
    scene = build(
        "import QtQuick\n"
        "Item { property int beats: 0\n"
        '  BlockIcon { id: icon; objectName: "probe"; block: "grass"; spinning: false }\n'
        "  Timer { interval: 16; repeat: true; running: true\n"
        "    onTriggered: if (icon.elapsed > 0) parent.beats++ } }"
    )
    run_animation(600)
    assert int(scene.property("beats")) == 0, "đồng hồ vẫn chạy dù icon đứng yên"


def find(scene: QObject, name: str) -> QObject:
    found = scene.findChild(QObject, name)
    assert found is not None, f"không thấy phần tử {name!r}"
    return found
