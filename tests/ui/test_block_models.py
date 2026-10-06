"""Kệ sách dùng mặt ván sồi; beacon phải nhìn xuyên kính thấy lõi và đế khi xoay."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QColor, QImage

from nostalgia.ui.block_textures import faces_from_jar, fallback_faces
from nostalgia.ui.blocks import ensure_strips, render_frame

pytestmark = pytest.mark.usefixtures("qt_app")


def texture_jar(tmp_path: Path, size: int) -> Path:
    jar_path = tmp_path / "client.jar"
    assets_dir = (
        Path(__file__).resolve().parents[2] / "src/nostalgia/ui/qml/assets/minecraft-blocks"
    )
    with zipfile.ZipFile(jar_path, "w") as archive:
        for path in (assets_dir / "models").rglob("*.json"):
            archive.write(path, f"assets/minecraft/{path.relative_to(assets_dir)}")
        for name, colour in (
            ("oak_planks", "#cf9852"),
            ("bookshelf", "#b03030"),
            ("beacon", "#00ff00"),
            ("obsidian", "#0000ff"),
        ):
            image = QImage(size, size, QImage.Format.Format_ARGB32)
            image.fill(QColor(colour))
            path = tmp_path / f"{name}.png"
            assert image.save(str(path))
            archive.write(path, f"assets/minecraft/textures/block/{name}.png")
        path = tmp_path / "glass.png"
        assert (
            QImage(str(assets_dir / "textures/block/glass.png")).scaled(size, size).save(str(path))
        )
        archive.write(path, "assets/minecraft/textures/block/glass.png")
    return jar_path


def test_bookshelf_uses_oak_on_top_and_books_on_its_sides(tmp_path: Path) -> None:
    faces = faces_from_jar(texture_jar(tmp_path, 16), "bookshelf")
    assert faces is not None
    assert faces.top.pixelColor(8, 8) == QColor("#cf9852")
    assert faces.side.pixelColor(8, 8) == QColor("#b03030")


@pytest.mark.parametrize("size", [16, 32, 64])
def test_beacon_renders_glass_core_and_base_with_resource_pack_sized_textures(
    tmp_path: Path, size: int
) -> None:
    faces = faces_from_jar(texture_jar(tmp_path, size), "beacon")
    assert faces is not None and faces.model is not None
    assert faces.model.gui_rotation == (30.0, 225.0, 0.0)
    assert faces.model.gui_scale == (0.625, 0.625, 0.625)
    for angle in (45, 135, 225, 315):
        image = render_frame(faces, angle, 64)
        colours = [image.pixelColor(x, y) for y in range(64) for x in range(64)]
        assert any(c.alpha() > 200 and c.green() > 100 and c.blue() < 20 for c in colours)
        assert any(c.alpha() > 200 and c.blue() > 100 and c.green() < 20 for c in colours)
        assert any(c.alpha() > 200 and min(c.red(), c.green(), c.blue()) > 90 for c in colours)


def test_fallback_bookshelf_has_coloured_books_and_a_wooden_top() -> None:
    faces = fallback_faces("bookshelf")
    assert faces.top != faces.side
    colours = [faces.side.pixelColor(x, y) for y in range(16) for x in range(16)]
    assert any(c.blue() > c.red() for c in colours), "phải thấy gáy sách xanh"
    assert any(c.red() > c.green() * 1.5 for c in colours), "phải thấy gáy sách đỏ"


def test_bundled_models_and_textures_are_unchanged_official_client_assets() -> None:
    assets_dir = (
        Path(__file__).resolve().parents[2] / "src/nostalgia/ui/qml/assets/minecraft-blocks"
    )
    fields = json.loads((assets_dir / "source.json").read_text())
    assert fields["minecraft_version"] == "1.20.1"
    assert fields["client_sha1"] == "0c3ec587af28e5a785c0b4a7b8a30f9a8f78f838"
    for name, expected in fields["files"].items():
        assert hashlib.sha256((assets_dir / name).read_bytes()).hexdigest() == expected


def test_geometry_is_read_from_the_model_in_the_client_jar(tmp_path: Path) -> None:
    jar_path = texture_jar(tmp_path, 16)
    with zipfile.ZipFile(jar_path) as archive:
        payloads = {name: archive.read(name) for name in archive.namelist()}
    name = "assets/minecraft/models/block/beacon.json"
    fields = json.loads(payloads[name])
    fields["elements"] = [fields["elements"][2]]
    fields["elements"][0]["from"] = [6, 6, 6]
    fields["elements"][0]["to"] = [10, 10, 10]
    payloads[name] = json.dumps(fields).encode()
    with zipfile.ZipFile(jar_path, "w") as archive:
        for name, payload in payloads.items():
            archive.writestr(name, payload)
    faces = faces_from_jar(jar_path, "beacon")
    assert faces is not None
    image = render_frame(faces, 45, 64)
    opaque = sum(image.pixelColor(x, y).alpha() > 200 for y in range(64) for x in range(64))
    assert 0 < opaque < 200, "model trong jar phải quyết định hình học, không dùng khối tự dựng"


def test_old_cached_cubes_are_replaced_without_touching_the_original_files(tmp_path: Path) -> None:
    for block in ("beacon", "bookshelf"):
        stale = tmp_path / f"{block}_code.png"
        stale.write_bytes(b"old cube")
    made = ensure_strips(tmp_path, None)
    for block in ("beacon", "bookshelf"):
        assert made[block].name != f"{block}_code.png"
        assert not QImage(str(made[block])).isNull()
        assert (tmp_path / f"{block}_code.png").read_bytes() == b"old cube"
