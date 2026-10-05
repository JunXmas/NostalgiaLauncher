"""Mã QR cho URL xác minh Microsoft và chuỗi VietQR: từng ô phải khớp bộ mã hoá chuẩn.

Đây là loại code mà test tự viết rất dễ chỉ nghiệm lại giả định của chính người viết — vòng
mã hoá/giải mã tự kiểm sẽ xanh dù bit đặt sai chỗ, miễn cả hai bên đồng ý cùng lỗi. Nên test
gác thật ở đây là thư viện `qrcode` (bộ mã hoá độc lập, chỉ có trong nhóm `dev`, launcher
không bao giờ import) sinh cùng chuỗi và so TỪNG Ô.

Trước đây chỗ này gác bằng `zbarimg` — giải lại PNG và so chuỗi. Hai vấn đề, đã trả giá cả
hai: công cụ ấy không có trên máy dev lẫn CI nên test skip im lặng; và giải-lại-được là
tiêu chuẩn quá lỏng — máy quét vẫn đọc đúng khi byte đệm đảo thứ tự hoặc khi bản sao thứ
hai của ô định dạng đặt ngược bit, vì nó bỏ qua đệm và chỉ cần một bản sao lành. Cả hai lỗi
đó đều có thật trong file này và chỉ lộ ra khi so từng ô.
"""

from __future__ import annotations

import random
import string

import pytest

from nostalgia.auth.qr import MAX_ASCII_BYTES, encode_qr, qr_png_bytes

qrcode = pytest.importorskip("qrcode", reason="trọng tài QR độc lập: uv sync")
from qrcode.constants import ERROR_CORRECT_L  # noqa: E402
from qrcode.util import MODE_8BIT_BYTE, QRData  # noqa: E402

# Chuỗi VietQR thật (115 byte) — lý do `auth/qr.py` phải với tới cỡ lưới 6, và cỡ 6 là cỡ
# đầu tiên chia Reed-Solomon làm hai khối phải đan xen.
VIETQR_SAMPLE = (
    "00020101021238570010A00000072701270006970436011312345678901230208QRIBFTTA"
    "53037045802VN62200816UNG HO NOSTALGIA63041234"
)


def _reference_matrix(text: str) -> list[list[bool]]:
    """Cùng chuỗi, cùng mức ECC L, cùng mask 0 — dựng bằng thư viện ngoài."""
    encoder = qrcode.QRCode(error_correction=ERROR_CORRECT_L, border=0, mask_pattern=0)
    encoder.add_data(QRData(text.encode(), mode=MODE_8BIT_BYTE))
    encoder.make(fit=True)
    return [[bool(cell) for cell in row] for row in encoder.get_matrix()]


@pytest.mark.parametrize(
    "text",
    [
        "A",
        "https://microsoft.com/link",
        "https://microsoft.com/link?otc=ABCD1234",
        VIETQR_SAMPLE,
        # Biên của từng cỡ lưới: ô cuối vừa khít, rồi ô đầu của cỡ kế tiếp.
        *[f"{'x' * length}" for length in (17, 18, 32, 33, 53, 54, 78, 79, 106, 107)],
        "x" * MAX_ASCII_BYTES,
    ],
)
def test_every_module_matches_an_independent_encoder(text: str) -> None:
    qr = encode_qr(text)
    reference = _reference_matrix(text)
    assert qr.size == len(reference), "chọn sai cỡ lưới cho độ dài này"
    mismatched = [
        (row, col)
        for row in range(qr.size)
        for col in range(qr.size)
        if qr.modules[row][col] != reference[row][col]
    ]
    assert not mismatched, f"lệch {len(mismatched)} ô so với bộ mã hoá chuẩn: {mismatched[:6]}"


def test_random_strings_across_every_size_class_match_too() -> None:
    """Chuỗi cố định chỉ đi qua vài nhánh. Sai một ô là máy quét đọc ra chuỗi khác — với mã
    chuyển khoản nghĩa là tiền đi nhầm chỗ, nên quét cả dải độ dài chứ không lấy mẫu."""
    generator = random.Random(20261001)
    sizes_seen = set()
    for _ in range(200):
        length = generator.randint(1, MAX_ASCII_BYTES)
        text = "".join(generator.choice(string.printable[:95]) for _ in range(length))
        qr = encode_qr(text)
        sizes_seen.add(qr.size)
        assert [list(row) for row in qr.modules] == _reference_matrix(text), text
    assert sizes_seen == {21, 25, 29, 33, 37, 41}, f"chưa chạm hết 6 cỡ lưới: {sorted(sizes_seen)}"


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
