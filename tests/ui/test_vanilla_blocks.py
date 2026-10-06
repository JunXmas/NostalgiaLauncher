"""Mọi khối có model gốc; grass giữ dirt/overlay/tint, các mặt khác không bị tráo."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from PySide6.QtGui import QImage

from nostalgia.ui.block_model import load_block_model
from nostalgia.ui.block_textures import BLOCK_MODELS, fallback_faces
from nostalgia.ui.blocks import ensure_strips
from nostalgia.ui.home_scene import render_home_scene, scene_blocks

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("block", list(BLOCK_MODELS))
def test_every_ui_icon_uses_original_model_even_without_a_client(block: str) -> None:
    faces = fallback_faces(block)
    assert faces.model is not None and len(faces.model.surfaces) >= 6
    assert not faces.top.isNull() and not faces.side.isNull()


def test_grass_uses_plains_tint_and_separate_dirt_bottom_and_side_overlay() -> None:
    model = load_block_model("grass_block")
    top = next(face.texture for face in model.surfaces if face.face == "top")
    bottom = next(face.texture for face in model.surfaces if face.face == "bottom")
    assert top != bottom
    assert all(
        top.pixelColor(x, y).green() > top.pixelColor(x, y).red()
        for y in range(16)
        for x in range(16)
    )
    assert any(face.face == "front" and face.layer == 2 for face in model.surfaces)
    crafting = load_block_model("crafting_table")
    sides = [face.texture for face in crafting.surfaces if face.face in ("front", "left")]
    assert sides[0] != sides[1], (
        "bàn chế tạo có các mặt khác nhau, không dùng một texture cho cả khối"
    )


def test_all_old_procedural_icons_are_replaced(tmp_path: Path) -> None:
    for block in BLOCK_MODELS:
        (tmp_path / f"{block}_code.png").write_bytes(b"old procedural texture")
    made = ensure_strips(tmp_path, None)
    for block, path in made.items():
        assert path.name.endswith("_v5_vanilla.png")
        assert not QImage(str(path)).isNull()
        assert (tmp_path / f"{block}_code.png").read_bytes() == b"old procedural texture"


def test_home_image_is_reproducible_from_vanilla_models() -> None:
    assets_dir = Path(__file__).resolve().parents[2] / "src/nostalgia/ui/qml/assets"
    image = QImage(str(assets_dir / "home-island.png"))
    assert not image.isNull() and image.hasAlphaChannel()
    assert image == render_home_scene(image.width())
    assert image.pixelColor(0, 0).alpha() == 0
    assert {placed.block for placed in scene_blocks()} >= {
        "grass_block",
        "oak_log",
        "oak_leaves",
        "crafting_table",
        "glowstone",
    }
