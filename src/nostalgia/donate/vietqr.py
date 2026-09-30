"""Chuỗi VietQR (EMVCo) cho mã chuyển khoản — thuần tính toán, không chạm mạng lẫn đĩa.

Đây là chuỗi mà app ngân hàng đọc được để điền sẵn người nhận. Sai một ký tự là **tiền đi
nhầm chỗ**, nên mọi thứ ở đây kiểm được bằng số: cấu trúc là thẻ TLV lồng nhau (mỗi thẻ là
`<mã 2 chữ số><độ dài 2 chữ số><nội dung>`), và bốn ký tự cuối là CRC-16/CCITT-FALSE của
toàn bộ phần đứng trước nó.

KHÔNG nhúng số tiền. Đây là tiền ủng hộ tuỳ tâm: gắn một con số vào mã là mặc định hộ người
khác họ nên cho bao nhiêu. Người ủng hộ tự gõ trong app ngân hàng của họ.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

# Định danh dịch vụ VietQR trong thẻ 38 — hằng của chuẩn NAPAS, không phải của dự án.
VIETQR_GUID = "A000000727"
SERVICE_TRANSFER_TO_ACCOUNT = "QRIBFTTA"  # chuyển tới TÀI KHOẢN (khác QRIBFTTC: tới thẻ)
CURRENCY_VND = "704"
COUNTRY_VN = "VN"
# Trần của chính chuẩn EMVCo cho thẻ nội dung chuyển khoản (thẻ 62 ô 08).
MAX_MEMO_LENGTH = 25


@dataclass(frozen=True, slots=True)
class BankAccount:
    """Tài khoản nhận tiền. `bin` là mã ngân hàng 6 chữ số theo bảng NAPAS (vd Vietcombank
    970436), KHÔNG phải mã SWIFT."""

    bin: str
    number: str
    holder: str


def crc16_ccitt(text: str) -> str:
    """CRC-16/CCITT-FALSE, in ra 4 chữ số hex hoa — đúng cách EMVCo khai trong thẻ 63.

    Vector chuẩn của thuật toán này: `crc16_ccitt("123456789") == "29B1"`. Có test gác, vì
    một bảng CRC sai vẫn cho ra chuỗi trông hợp lệ mà app ngân hàng từ chối đọc.
    """
    register = 0xFFFF
    for byte in text.encode("ascii"):
        register ^= byte << 8
        for _ in range(8):
            register = ((register << 1) ^ 0x1021) & 0xFFFF if register & 0x8000 else register << 1
            register &= 0xFFFF
    return f"{register:04X}"


def normalize_memo(text: str) -> str:
    """Bỏ dấu, viết hoa, chỉ giữ chữ-số-khoảng trắng, cắt còn `MAX_MEMO_LENGTH` ký tự.

    Nội dung chuyển khoản đi qua hệ thống liên ngân hàng, nơi ký tự có dấu bị thay bằng rác
    hoặc làm ngân hàng từ chối lệnh. Bỏ dấu ở đây chứ không bắt người gọi nhớ.
    """
    # `Đ`/`đ` là ký tự RIÊNG trong Unicode, không phải `D` cộng dấu, nên NFD không tách được
    # — phải thay tay. Bỏ sót thì nó lọt qua vòng lọc `isalnum()` (nó vẫn là chữ cái) và
    # `encode("ascii")` ở tầng QR ném lỗi, đúng lúc người dùng bấm nút.
    stripped = unicodedata.normalize("NFD", text.replace("Đ", "D").replace("đ", "d"))
    ascii_only = "".join(char for char in stripped if unicodedata.category(char) != "Mn")
    kept = "".join(
        char if char.isascii() and char.isalnum() else " " for char in ascii_only.upper()
    )
    return " ".join(kept.split())[:MAX_MEMO_LENGTH]


def _tag(code: str, value: str) -> str:
    if len(value) > 99:
        message = f"thẻ {code} dài {len(value)} ký tự, chuẩn EMVCo chỉ cho tối đa 99"
        raise ValueError(message)
    return f"{code}{len(value):02d}{value}"


def vietqr_payload(account: BankAccount, memo: str) -> str:
    """Chuỗi VietQR hoàn chỉnh (đã có CRC ở cuối) cho một lần chuyển khoản không định sẵn tiền.

    Mã khai là loại DÙNG NHIỀU LẦN (thẻ 01 = "11"): mã ủng hộ nằm im trong CÀI ĐẶT, ai quét
    lúc nào cũng được. Khai "12" (dùng một lần) thì có app ngân hàng từ chối quét lần thứ hai.
    """
    if not account.bin.isdigit() or not account.number.isdigit():
        message = (
            "mã ngân hàng và số tài khoản phải toàn chữ số, "
            f"nhận {account.bin!r}/{account.number!r}"
        )
        raise ValueError(message)
    beneficiary = _tag("00", account.bin) + _tag("01", account.number)
    body = _tag("00", "01") + _tag("01", "11")
    body += _tag(
        "38",
        _tag("00", VIETQR_GUID) + _tag("01", beneficiary) + _tag("02", SERVICE_TRANSFER_TO_ACCOUNT),
    )
    body += _tag("53", CURRENCY_VND) + _tag("58", COUNTRY_VN)
    normalized = normalize_memo(memo)
    if normalized:
        body += _tag("62", _tag("08", normalized))
    # "6304" là mã thẻ 63 + độ dài 04 của chính CRC; CRC tính TRÊN CẢ hai ký tự đó.
    body += "6304"
    return body + crc16_ccitt(body)


__all__ = [
    "MAX_MEMO_LENGTH",
    "BankAccount",
    "crc16_ccitt",
    "normalize_memo",
    "vietqr_payload",
]
