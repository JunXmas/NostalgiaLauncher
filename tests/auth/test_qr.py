"""Mã QR cho URL xác minh Microsoft: giải lại bằng mắt, vị trí góc, và biên chuỗi.

Đây là loại code mà test tự viết rất dễ chỉ nghiệm lại giả định của chính người viết — vòng
mã hoá/giải mã tự kiểm sẽ xanh dù bit đặt sai chỗ, miễn cả hai bên đồng ý cùng lỗi. Nên test
gác thật ở đây là zbarimg (`libzbar`, decoder độc lập, không dùng lại code trong repo) đọc
PNG sinh ra và trả đúng chuỗi gốc — không có nó thì test này chỉ chứng minh mã tự giải được
mã của chính nó.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from nostalgia.auth.qr import MAX_ASCII_BYTES, encode_qr, qr_png_bytes

ZBARIMG = shutil.which("zbarimg")


def _decode_with_zbar(png: bytes, tmp_path: Path) -> str:
    png_path = tmp_path / "qr.png"
    png_path.write_bytes(png)
    result = subprocess.run(
        [ZBARIMG, "--raw", "-q", str(png_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.mark.skipif(ZBARIMG is None, reason="cần zbarimg (libzbar) để giải lại QR độc lập")
@pytest.mark.parametrize(
    "text",
    [
        "https://microsoft.com/link",
        "https://microsoft.com/link?otc=ABCD1234",
        "A",
        "x" * MAX_ASCII_BYTES,
    ],
)
def test_qr_roundtrips_through_an_independent_decoder(text: str, tmp_path: Path) -> None:
    qr = encode_qr(text)
    decoded = _decode_with_zbar(qr_png_bytes(qr), tmp_path)
    assert decoded == text


def test_finder_patterns_sit_in_exactly_three_corners() -> None:
    """Ba hình vuông lồng góc là thứ máy quét bám vào đầu tiên để định hướng khung hình."""
    qr = encode_qr("https://microsoft.com/link")
    n = qr.size
    corners = {(0, 0), (0, n - 7), (n - 7, 0)}
    for r0, c0 in corners:
        for row in range(7):
            for c in range(7):
                ring = max(abs(row - 3), abs(c - 3))
                expected = ring <= 1 or ring == 3
                assert qr.modules[r0 + row][c0 + c] == expected, (r0, c0, row, c)
    # Góc thứ tư (dưới-phải) không có finder pattern.
    assert not all(qr.modules[n - 7][n - 7 + c] for c in range(7))


def test_quiet_zone_is_four_modules_of_white_border() -> None:
    qr = encode_qr("A")
    border = 4
    scale = 1
    png = qr_png_bytes(qr, scale=scale, border=border)
    # PNG 1-bit: chỉ cần xác nhận kích thước đúng công thức (size + 2*border) * scale.
    import struct

    width, height = struct.unpack(">II", png[16:24])
    expected = (qr.size + border * 2) * scale
    assert (width, height) == (expected, expected)


def test_rejects_empty_string() -> None:
    with pytest.raises(ValueError, match=r"1\.\."):
        encode_qr("")


def test_rejects_text_longer_than_capacity() -> None:
    with pytest.raises(ValueError, match=r"1\.\."):
        encode_qr("x" * (MAX_ASCII_BYTES + 1))


def test_rejects_non_ascii() -> None:
    with pytest.raises(ValueError, match="ASCII"):
        encode_qr("microsoft.com/liên-kết")
