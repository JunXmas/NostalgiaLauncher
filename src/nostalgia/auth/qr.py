"""Mã QR tối thiểu cho URL xác minh Microsoft, không phụ thuộc thư viện ngoài.

Chỉ đủ cho việc thật sự cần: chuỗi ASCII ngắn (URL device-code, dưới 60 ký tự), một mức
sửa lỗi (L — thấp nhất, đủ cho ảnh hiển thị sạch trên màn hình chứ không in ra rồi làm nhàu),
và cỡ lưới nhỏ nhất vừa khít dữ liệu (version 1-4 của chuẩn QR). Không hỗ trợ Kanji, chế độ
số, hay các mức ECC khác — thêm vào là code không ai gọi tới.

Toạ độ mask cố định (mask 0, bàn cờ `(row+col)%2==0`): chuẩn QR không đòi mask phải tối ưu,
chỉ đòi số mask đã dùng được ghi đúng vào ô định dạng để đầu đọc biết cách đảo lại — máy quét
đọc đúng bất kể mask nào miễn khai đúng. Chọn cố định để khỏi cài thêm bước chấm điểm 4 kiểu
phạt của chuẩn, thứ chỉ có giá trị khi cần nén ảnh nhỏ nhất, không phải khi cần đọc được.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

MAX_ASCII_BYTES = 78  # sức chứa cỡ lưới 4 mức ECC L — trần trên loại QR này hỗ trợ.

_MASK_ID = 0
_PAD_BYTES = (0xEC, 0x11)
_FORMAT_GENERATOR = 0b10100110111
_FORMAT_MASK = 0b101010000010010

# cỡ lưới -> (số codeword dữ liệu, số codeword sửa lỗi, sức chứa byte tối đa, vị trí ô canh)
_SIZE_CLASSES: dict[int, tuple[int, int, int, int | None]] = {
    1: (19, 7, 17, None),
    2: (34, 10, 32, 18),
    3: (55, 15, 53, 22),
    4: (80, 20, 78, 26),
}

_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


@dataclass(frozen=True, slots=True)
class QrCode:
    """Lưới module vuông. `modules[hàng][cột]` là `True` khi ô đó tối."""

    modules: tuple[tuple[bool, ...], ...]

    @property
    def size(self) -> int:
        return len(self.modules)

    def render_ascii(self) -> str:
        """Ma trận in được ra terminal — dùng để soát bằng mắt trước khi quét thật."""
        return "\n".join("".join("██" if cell else "  " for cell in row) for row in self.modules)


def encode_qr(text: str) -> QrCode:
    """Mã hoá `text` (ASCII, 1-78 byte) thành mã QR mức sửa lỗi L."""
    try:
        payload = text.encode("ascii")
    except UnicodeEncodeError as error:
        message = "QR ở đây chỉ mã hoá ASCII"
        raise ValueError(message) from error
    if not payload or len(payload) > MAX_ASCII_BYTES:
        message = f"độ dài phải trong khoảng 1..{MAX_ASCII_BYTES} byte ASCII, nhận {len(payload)}"
        raise ValueError(message)

    size_class = next(sc for sc, (_, _, cap, _) in _SIZE_CLASSES.items() if len(payload) <= cap)
    codewords = _build_codewords(payload, size_class)
    return QrCode(modules=_build_matrix(codewords, size_class))


def qr_png_bytes(qr: QrCode, *, scale: int = 8, border: int = 4) -> bytes:
    """PNG 1-bit đen trắng, phóng `scale` lần với viền trắng `border` ô quanh mã."""
    n = qr.size
    size = (n + border * 2) * scale
    row_bytes = (size + 7) // 8
    raw = bytearray()
    for py in range(size):
        raw.append(0)  # filter byte: "none"
        row = bytearray(row_bytes)
        my = py // scale - border
        dark_row = qr.modules[my] if 0 <= my < n else None
        for px in range(size):
            mx = px // scale - border
            dark = dark_row is not None and 0 <= mx < n and dark_row[mx]
            if not dark:
                row[px // 8] |= 0x80 >> (px % 8)
        raw.extend(row)
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(tag: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))

    ihdr = struct.pack(">IIBBBBB", size, size, 1, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _rs_generator(degree: int) -> list[int]:
    g = [1]
    for i in range(degree):
        g = [_gf_mul(c, _EXP[i]) ^ (g[j - 1] if j > 0 else 0) for j, c in enumerate([*g, 0])]
    return list(reversed(g))


def _rs_encode(codewords: list[int], ec_len: int) -> list[int]:
    generator = _rs_generator(ec_len)
    residue = codewords + [0] * ec_len
    for i in range(len(codewords)):
        factor = residue[i]
        if factor == 0:
            continue
        for j, gcoef in enumerate(generator):
            residue[i + j] ^= _gf_mul(gcoef, factor)
    return residue[len(codewords):]


def _build_codewords(payload: bytes, size_class: int) -> list[int]:
    data_cw, ec_cw, _, _ = _SIZE_CLASSES[size_class]
    bits = "0100" + format(len(payload), "08b")
    for byte in payload:
        bits += format(byte, "08b")
    bits += "0000"[: max(0, min(4, data_cw * 8 - len(bits)))]
    bits += "0" * (-len(bits) % 8)
    codewords = [int(bits[i : i + 8], 2) for i in range(0, len(bits), 8)]
    for i in range(len(codewords), data_cw):
        codewords.append(_PAD_BYTES[i % 2])
    return codewords + _rs_encode(codewords, ec_cw)


def _format_bits() -> int:
    payload = (0b01 << 3) | _MASK_ID  # 01 = mức sửa lỗi L theo bảng chuẩn QR
    remainder = payload << 10
    for i in range(4, -1, -1):
        if remainder & (1 << (i + 10)):
            remainder ^= _FORMAT_GENERATOR << i
    return ((payload << 10) | (remainder & 0x3FF)) ^ _FORMAT_MASK


def _place_finder(matrix: list[list[bool]], reserved: list[list[bool]], r0: int, c0: int) -> None:
    n = len(matrix)
    for dr in range(-1, 8):
        for c in range(-1, 8):
            rr, cc = r0 + dr, c0 + c
            if not (0 <= rr < n and 0 <= cc < n):
                continue
            reserved[rr][cc] = True
            in_finder = 0 <= dr <= 6 and 0 <= c <= 6
            ring = max(abs(dr - 3), abs(c - 3))
            matrix[rr][cc] = in_finder and (ring <= 1 or ring == 3)


def _build_matrix(codewords: list[int], size_class: int) -> tuple[tuple[bool, ...], ...]:
    _, _, _, align = _SIZE_CLASSES[size_class]
    n = 4 * size_class + 17
    matrix = [[False] * n for _ in range(n)]
    reserved = [[False] * n for _ in range(n)]

    _place_finder(matrix, reserved, 0, 0)
    _place_finder(matrix, reserved, 0, n - 7)
    _place_finder(matrix, reserved, n - 7, 0)

    for i in range(n):
        if not reserved[6][i]:
            reserved[6][i] = True
            matrix[6][i] = i % 2 == 0
        if not reserved[i][6]:
            reserved[i][6] = True
            matrix[i][6] = i % 2 == 0

    if align is not None:
        for row in range(align - 2, align + 3):
            for c in range(align - 2, align + 3):
                reserved[row][c] = True
                matrix[row][c] = max(abs(row - align), abs(c - align)) != 1

    matrix[4 * size_class + 9][8] = True  # module tối cố định, dark module của chuẩn QR
    reserved[4 * size_class + 9][8] = True

    for c in range(9):
        reserved[8][c] = True
    for row in range(9):
        reserved[row][8] = True
    for c in range(n - 8, n):
        reserved[8][c] = True
    for row in range(n - 7, n):
        reserved[row][8] = True

    bitstream = "".join(format(b, "08b") for b in codewords)
    bit_index = 0
    col = n - 1
    upward = True
    while col > 0:
        if col == 6:
            col -= 1
            continue
        rows = range(n - 1, -1, -1) if upward else range(n)
        for row in rows:
            for c in (col, col - 1):
                if reserved[row][c]:
                    continue
                bit = bitstream[bit_index] if bit_index < len(bitstream) else "0"
                bit_index += 1
                dark = bit == "1"
                if (row + c) % 2 == 0:
                    dark = not dark
                matrix[row][c] = dark
        upward = not upward
        col -= 2

    _place_format_info(matrix, n)
    return tuple(tuple(row) for row in matrix)


def _place_format_info(matrix: list[list[bool]], n: int) -> None:
    bits = format(_format_bits(), "015b")
    for i in range(6):
        matrix[8][i] = bits[i] == "1"
    matrix[8][7] = bits[6] == "1"
    matrix[8][8] = bits[7] == "1"
    matrix[7][8] = bits[8] == "1"
    for i in range(9, 15):
        matrix[14 - i][8] = bits[i] == "1"
    for i in range(8):
        matrix[8][n - 1 - i] = bits[i] == "1"
    for i in range(8, 15):
        matrix[n - 15 + i][8] = bits[i] == "1"


__all__ = ["MAX_ASCII_BYTES", "QrCode", "encode_qr", "qr_png_bytes"]
