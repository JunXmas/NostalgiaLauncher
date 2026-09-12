"""Đọc/ghi ảnh PNG RGBA 64×64 dùng thư viện chuẩn — không cần Pillow hay OpenCV.

Minecraft skin dùng PNG 64×64 với 4 kênh RGBA. Module này cung cấp bộ tiện ích tối thiểu
cho bước đầu của trình vẽ skin tích hợp: nạp texture ra lưới điểm ảnh, sửa từng điểm,
tô vùng, và lưu lại thành PNG nguyên vẹn.

**Không có thư viện ngoài.** Đọc PNG bằng `struct` để tháo các chunk, giải nén dữ liệu ảnh
bằng `zlib`, và ghi ngược lại cũng bằng `struct` + `zlib`. Chỉ hỗ trợ đúng kiểu ảnh mà
Minecraft skin cần: color type 6 (RGBA), bit depth 8, không interlace.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

# Kích thước duy nhất hợp lệ cho skin Minecraft 64×64.
SKIN_WIDTH = 64
SKIN_HEIGHT = 64

# Hằng PNG.
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_COLOR_TYPE_RGBA = 6
_BIT_DEPTH_8 = 8
_FILTER_NONE = 0

# Kiểu một điểm ảnh: (R, G, B, A), mỗi kênh 0–255.
type Rgba = tuple[int, int, int, int]

# Lưới điểm ảnh: danh sách các hàng, mỗi hàng là danh sách RGBA.
type PixelGrid = list[list[Rgba]]


@dataclass(frozen=True, slots=True)
class SkinTexture:
    """Một texture skin đã nạp xong, sẵn sàng cho trình vẽ sửa."""

    width: int
    height: int
    pixels: PixelGrid


def load_texture(path: Path) -> SkinTexture:
    """Đọc file PNG RGBA 64×64 và trả về ``SkinTexture``.

    Chỉ chấp nhận ảnh đúng kích thước 64×64, color type 6, bit depth 8, không interlace.
    Ném ``ValueError`` nếu file không thoả mãn.
    """
    raw = path.read_bytes()
    if raw[:8] != _PNG_SIGNATURE:
        message = f"{path}: không phải file PNG"
        raise ValueError(message)

    width, height, pixels_data = _decode_png_rgba(raw)
    if width != SKIN_WIDTH or height != SKIN_HEIGHT:
        message = f"{path}: kích thước {width}×{height}, cần {SKIN_WIDTH}×{SKIN_HEIGHT}"
        raise ValueError(message)

    grid = _raw_to_grid(pixels_data, width, height)
    return SkinTexture(width=width, height=height, pixels=grid)


def save_texture(grid: PixelGrid, path: Path) -> None:
    """Ghi lưới điểm ảnh RGBA ra file PNG 64×64."""
    height = len(grid)
    width = len(grid[0]) if height else 0
    raw = _grid_to_raw(grid, width, height)
    png_bytes = _encode_png_rgba(raw, width, height)
    path.write_bytes(png_bytes)


def apply_pixel(grid: PixelGrid, x: int, y: int, rgba: Rgba) -> None:
    """Đặt một điểm ảnh tại ``(x, y)``. Ném ``IndexError`` nếu ra ngoài biên."""
    height = len(grid)
    width = len(grid[0]) if height else 0
    if not (0 <= x < width and 0 <= y < height):
        message = f"toạ độ ({x}, {y}) ngoài biên {width}×{height}"
        raise IndexError(message)
    grid[y][x] = rgba


def fill_region(grid: PixelGrid, x: int, y: int, rgba: Rgba) -> None:
    """Tô vùng liên thông cùng màu bắt đầu từ ``(x, y)`` — kiểu thùng sơn.

    Dùng BFS để tránh tràn stack trên vùng lớn. Chỉ lan sang bốn hướng (trên, dưới, trái, phải).
    """
    height = len(grid)
    width = len(grid[0]) if height else 0
    if not (0 <= x < width and 0 <= y < height):
        return
    target_color = grid[y][x]
    if target_color == rgba:
        return

    queue: list[tuple[int, int]] = [(x, y)]
    visited: set[tuple[int, int]] = {(x, y)}
    while queue:
        cx, cy = queue.pop(0)
        grid[cy][cx] = rgba
        for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                if grid[ny][nx] == target_color:
                    visited.add((nx, ny))
                    queue.append((nx, ny))


# --- Nội bộ: đọc/ghi PNG ---


def _read_chunks(png_content: bytes) -> list[tuple[bytes, bytes]]:
    """Tháo các chunk PNG ra danh sách ``(chunk_type, chunk_data)``."""
    chunks: list[tuple[bytes, bytes]] = []
    offset = 8  # bỏ qua chữ ký
    while offset < len(png_content):
        length = struct.unpack(">I", png_content[offset : offset + 4])[0]
        chunk_type = png_content[offset + 4 : offset + 8]
        chunk_data = png_content[offset + 8 : offset + 8 + length]
        chunks.append((chunk_type, chunk_data))
        offset += 12 + length  # 4 length + 4 type + chunk_data + 4 crc
    return chunks


def _decode_png_rgba(png_content: bytes) -> tuple[int, int, bytes]:
    """Giải mã PNG thành ``(width, height, raw_rgba_bytes)``."""
    chunks = _read_chunks(png_content)
    ihdr_content = next(d for t, d in chunks if t == b"IHDR")
    width, height, bit_depth, color_type = struct.unpack(">IIBB", ihdr_content[:10])
    compression, _filter_method, interlace = struct.unpack("BBB", ihdr_content[10:13])

    if color_type != _COLOR_TYPE_RGBA:
        message = f"color type {color_type}, cần {_COLOR_TYPE_RGBA} (RGBA)"
        raise ValueError(message)
    if bit_depth != _BIT_DEPTH_8:
        message = f"bit depth {bit_depth}, cần {_BIT_DEPTH_8}"
        raise ValueError(message)
    if interlace != 0:
        message = "PNG interlace không được hỗ trợ"
        raise ValueError(message)

    compressed = b"".join(d for t, d in chunks if t == b"IDAT")
    decompressed = zlib.decompress(compressed)
    pixels = _unfilter(decompressed, width, height)
    return width, height, pixels


def _unfilter(scanlines: bytes, width: int, height: int) -> bytes:
    """Bỏ filter byte đầu mỗi hàng quét và khôi phục dữ liệu gốc.

    Hỗ trợ đủ 5 kiểu filter PNG (None, Sub, Up, Average, Paeth) để đọc được mọi file PNG
    mà encoder ngoài tạo ra.
    """
    stride = width * 4  # 4 byte mỗi pixel (RGBA)
    result = bytearray(height * stride)
    offset = 0

    for y in range(height):
        filter_type = scanlines[offset]
        offset += 1
        row_start = y * stride
        prev_row_start = (y - 1) * stride

        for i in range(stride):
            raw_byte = scanlines[offset]
            offset += 1

            if filter_type == 0:  # None
                value = raw_byte
            elif filter_type == 1:  # Sub
                left = result[row_start + i - 4] if i >= 4 else 0
                value = (raw_byte + left) & 0xFF
            elif filter_type == 2:  # Up
                up = result[prev_row_start + i] if y > 0 else 0
                value = (raw_byte + up) & 0xFF
            elif filter_type == 3:  # Average
                left = result[row_start + i - 4] if i >= 4 else 0
                up = result[prev_row_start + i] if y > 0 else 0
                value = (raw_byte + (left + up) // 2) & 0xFF
            elif filter_type == 4:  # Paeth
                left = result[row_start + i - 4] if i >= 4 else 0
                up = result[prev_row_start + i] if y > 0 else 0
                up_left = result[prev_row_start + i - 4] if y > 0 and i >= 4 else 0
                value = (raw_byte + _paeth_predictor(left, up, up_left)) & 0xFF
            else:
                message = f"filter type {filter_type} không được hỗ trợ"
                raise ValueError(message)

            result[row_start + i] = value
    return bytes(result)


def _paeth_predictor(left: int, up: int, up_left: int) -> int:
    """Bộ dự đoán Paeth — thuật toán chuẩn trong đặc tả PNG."""
    estimate = left + up - up_left
    dist_left = abs(estimate - left)
    dist_up = abs(estimate - up)
    dist_up_left = abs(estimate - up_left)
    if dist_left <= dist_up and dist_left <= dist_up_left:
        return left
    if dist_up <= dist_up_left:
        return up
    return up_left


def _raw_to_grid(pixel_bytes: bytes, width: int, height: int) -> PixelGrid:
    """Chuyển bytes RGBA thẳng thành lưới ``list[list[Rgba]]``."""
    grid: PixelGrid = []
    for y in range(height):
        row: list[Rgba] = []
        for x in range(width):
            base = (y * width + x) * 4
            row.append((
                pixel_bytes[base], pixel_bytes[base + 1],
                pixel_bytes[base + 2], pixel_bytes[base + 3],
            ))
        grid.append(row)
    return grid


def _grid_to_raw(grid: PixelGrid, width: int, height: int) -> bytes:
    """Chuyển lưới RGBA thành bytes phẳng."""
    result = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = grid[y][x]
            base = (y * width + x) * 4
            result[base] = red
            result[base + 1] = green
            result[base + 2] = blue
            result[base + 3] = alpha
    return bytes(result)


def _encode_png_rgba(raw: bytes, width: int, height: int) -> bytes:
    """Ghi dữ liệu RGBA thành file PNG hoàn chỉnh, filter None cho mọi hàng."""
    # IHDR
    ihdr_content = struct.pack(
        ">IIBBBBB", width, height, _BIT_DEPTH_8, _COLOR_TYPE_RGBA, 0, 0, 0
    )
    # Thêm filter byte (0 = None) đầu mỗi hàng rồi nén
    filtered = bytearray()
    stride = width * 4
    for y in range(height):
        filtered.append(_FILTER_NONE)
        filtered.extend(raw[y * stride : (y + 1) * stride])
    compressed = zlib.compress(bytes(filtered))

    output = bytearray(_PNG_SIGNATURE)
    output.extend(_make_chunk(b"IHDR", ihdr_content))
    output.extend(_make_chunk(b"IDAT", compressed))
    output.extend(_make_chunk(b"IEND", b""))
    return bytes(output)


def _make_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    """Đóng gói một chunk PNG: length + type + payload + crc32."""
    crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", crc)
