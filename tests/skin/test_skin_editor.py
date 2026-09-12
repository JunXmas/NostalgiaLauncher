"""Trình chỉnh sửa skin: nạp, sửa điểm ảnh, tô vùng, lưu — không cần Pillow."""

from __future__ import annotations

from pathlib import Path

import pytest

from nostalgia.skin.editor import (
    SKIN_HEIGHT,
    SKIN_WIDTH,
    SkinTexture,
    apply_pixel,
    fill_region,
    load_texture,
    save_texture,
)


def _make_solid_grid(
    width: int = SKIN_WIDTH,
    height: int = SKIN_HEIGHT,
    rgba: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> list[list[tuple[int, int, int, int]]]:
    """Tạo lưới đồng màu."""
    return [[rgba for _ in range(width)] for _ in range(height)]


def test_save_then_load_round_trips_a_transparent_skin(tmp_path: Path) -> None:
    """Ghi rồi đọc lại phải trả về dữ liệu y hệt — kiểm trọn vẹn bộ mã hoá/giải mã."""
    grid = _make_solid_grid()
    path = tmp_path / "transparent.png"
    save_texture(grid, path)
    texture = load_texture(path)

    assert texture.width == SKIN_WIDTH
    assert texture.height == SKIN_HEIGHT
    assert texture.pixels == grid


def test_save_then_load_round_trips_an_opaque_skin(tmp_path: Path) -> None:
    """Ảnh có nội dung thật (không toàn 0) cũng phải round-trip."""
    grid = _make_solid_grid(rgba=(200, 100, 50, 255))
    path = tmp_path / "opaque.png"
    save_texture(grid, path)
    texture = load_texture(path)

    assert texture.pixels == grid


def test_apply_pixel_changes_exactly_one_pixel() -> None:
    grid = _make_solid_grid(rgba=(0, 0, 0, 255))
    apply_pixel(grid, 10, 20, (255, 0, 0, 255))

    assert grid[20][10] == (255, 0, 0, 255)
    assert grid[0][0] == (0, 0, 0, 255), "không đụng pixel khác"
    assert grid[20][11] == (0, 0, 0, 255), "pixel kế bên vẫn nguyên"


def test_apply_pixel_out_of_bounds_raises_index_error() -> None:
    grid = _make_solid_grid()
    with pytest.raises(IndexError):
        apply_pixel(grid, 64, 0, (255, 0, 0, 255))
    with pytest.raises(IndexError):
        apply_pixel(grid, 0, 64, (255, 0, 0, 255))
    with pytest.raises(IndexError):
        apply_pixel(grid, -1, 0, (255, 0, 0, 255))


def test_fill_region_fills_a_connected_same_color_area() -> None:
    """Tô vùng kiểu thùng sơn: chỉ lan sang pixel cùng màu, dừng tại biên khác màu."""
    grid = _make_solid_grid(width=8, height=8, rgba=(0, 0, 0, 255))
    # Vẽ hàng rào quanh vùng 3×3 góc trên trái
    barrier = (255, 255, 255, 255)
    for i in range(4):
        grid[3][i] = barrier  # hàng ngang
        grid[i][3] = barrier  # cột dọc

    fill_region(grid, 0, 0, (0, 255, 0, 255))

    # Bên trong hàng rào phải được tô
    assert grid[0][0] == (0, 255, 0, 255)
    assert grid[2][2] == (0, 255, 0, 255)
    # Hàng rào không bị đụng
    assert grid[3][0] == barrier
    assert grid[0][3] == barrier
    # Bên ngoài hàng rào vẫn nguyên
    assert grid[4][4] == (0, 0, 0, 255)


def test_fill_region_does_nothing_when_target_equals_replacement() -> None:
    grid = _make_solid_grid(width=4, height=4, rgba=(100, 100, 100, 255))
    fill_region(grid, 0, 0, (100, 100, 100, 255))
    assert all(pixel == (100, 100, 100, 255) for row in grid for pixel in row)


def test_fill_region_out_of_bounds_is_harmless() -> None:
    """Gọi fill_region ngoài biên không ném lỗi, chỉ không làm gì."""
    grid = _make_solid_grid(width=4, height=4)
    fill_region(grid, 10, 10, (255, 0, 0, 255))
    assert all(pixel == (0, 0, 0, 0) for row in grid for pixel in row)


def test_modified_texture_survives_save_and_reload(tmp_path: Path) -> None:
    """Sửa pixel → lưu → đọc lại — kiểm trọn vẹn chuỗi chỉnh sửa."""
    grid = _make_solid_grid(rgba=(128, 128, 128, 255))
    apply_pixel(grid, 32, 32, (255, 0, 0, 255))
    apply_pixel(grid, 0, 0, (0, 255, 0, 128))

    path = tmp_path / "edited.png"
    save_texture(grid, path)
    reloaded = load_texture(path)

    assert reloaded.pixels[32][32] == (255, 0, 0, 255)
    assert reloaded.pixels[0][0] == (0, 255, 0, 128)
    assert reloaded.pixels[1][1] == (128, 128, 128, 255)


def test_load_texture_rejects_non_png(tmp_path: Path) -> None:
    bad = tmp_path / "not_a_png.png"
    bad.write_bytes(b"this is not a png file")
    with pytest.raises(ValueError, match="không phải file PNG"):
        load_texture(bad)


def test_load_texture_rejects_wrong_size(tmp_path: Path) -> None:
    """Skin phải chính xác 64×64; kích thước khác bị từ chối."""
    small_grid: list[list[tuple[int, int, int, int]]] = [
        [(0, 0, 0, 0) for _ in range(32)] for _ in range(32)
    ]
    path = tmp_path / "small.png"
    save_texture(small_grid, path)
    with pytest.raises(ValueError, match="32×32"):
        load_texture(path)


def test_skin_texture_is_frozen() -> None:
    """SkinTexture phải là dataclass frozen theo GLOSSARY §1.3."""
    texture = SkinTexture(width=64, height=64, pixels=[])
    with pytest.raises(AttributeError):
        texture.width = 128  # type: ignore[misc]
