"""Chuỗi VietQR: CRC khớp vector chuẩn, cấu trúc TLV đúng, và bóc ngược ra đúng tài khoản.

Sai một ký tự ở đây là tiền đi nhầm tài khoản, và không có cách nào biết cho đến khi ai đó
mất tiền. Nên test không dừng ở "hàm chạy không ném": nó bóc chuỗi ra lại theo đúng luật
TLV của EMVCo và đối chiếu từng thẻ.
"""

from __future__ import annotations

import pytest

from nostalgia.donate.vietqr import (
    MAX_MEMO_LENGTH,
    BankAccount,
    crc16_ccitt,
    normalize_memo,
    vietqr_payload,
)

ACCOUNT = BankAccount(bin="970436", number="1234567890", holder="NGUYEN VAN A")
MEMO = "UNG HO NOSTALGIA"


def parse_tlv(text: str) -> dict[str, str]:
    """Bóc một chuỗi EMVCo thành {mã thẻ: nội dung}. Cố ý viết lại ở đây, không dùng lại code
    trong kho: test bóc bằng chính hàm dựng thì chỉ chứng minh nó tự hiểu được nó."""
    tags: dict[str, str] = {}
    position = 0
    while position + 4 <= len(text):
        code, length = text[position : position + 2], int(text[position + 2 : position + 4])
        tags[code] = text[position + 4 : position + 4 + length]
        position += 4 + length
    return tags


def test_crc_matches_the_published_test_vector() -> None:
    """Vector chuẩn của CRC-16/CCITT-FALSE. Bảng CRC sai vẫn cho ra chuỗi trông hợp lệ mà
    app ngân hàng lặng lẽ từ chối đọc — không test này thì không có gì bắt được."""
    assert crc16_ccitt("123456789") == "29B1"


def test_payload_carries_the_account_and_no_amount() -> None:
    payload = vietqr_payload(ACCOUNT, MEMO)
    tags = parse_tlv(payload)

    assert tags["00"] == "01", "phiên bản EMVCo"
    assert tags["01"] == "11", "mã dùng NHIỀU LẦN: mã ủng hộ nằm im, ai quét lúc nào cũng được"
    assert tags["53"] == "704" and tags["58"] == "VN"
    assert "54" not in tags, "không nhúng số tiền: ủng hộ tuỳ tâm, người gửi tự gõ"

    beneficiary = parse_tlv(tags["38"])
    assert beneficiary["00"] == "A000000727", "định danh dịch vụ VietQR"
    assert beneficiary["02"] == "QRIBFTTA", "chuyển tới tài khoản, không phải tới thẻ"
    account = parse_tlv(beneficiary["01"])
    assert account == {"00": ACCOUNT.bin, "01": ACCOUNT.number}
    assert parse_tlv(tags["62"]) == {"08": MEMO}


def test_crc_covers_the_whole_string_including_its_own_tag_header() -> None:
    """Thẻ 63 tự nằm trong vùng được tính CRC — bỏ "6304" ra khỏi phép tính là lỗi kinh điển."""
    payload = vietqr_payload(ACCOUNT, MEMO)
    assert payload[-8:-4] == "6304"
    assert crc16_ccitt(payload[:-4]) == payload[-4:]


def test_payload_fits_the_qr_encoder() -> None:
    """115 byte — đây là con số buộc `auth/qr.py` phải với tới cỡ lưới 6. Chuỗi dài ra quá
    trần thì mã QR không dựng được và nút ủng hộ chết im lặng."""
    from nostalgia.auth.qr import MAX_ASCII_BYTES, encode_qr

    payload = vietqr_payload(BankAccount("970436", "0011001234567", "NGUYEN VAN A"), MEMO)
    assert len(payload) <= MAX_ASCII_BYTES
    assert encode_qr(payload).size == 41, "cỡ lưới 6"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Ủng hộ Nostalgia", "UNG HO NOSTALGIA"),
        ("ủng-hộ  nostalgia!", "UNG HO NOSTALGIA"),
        ("x" * 40, "X" * MAX_MEMO_LENGTH),
        ("Đặng Hà", "DANG HA"),
    ],
)
def test_memo_is_stripped_of_diacritics_and_capped(raw: str, expected: str) -> None:
    """Ký tự có dấu đi qua hệ thống liên ngân hàng thành rác, hoặc làm ngân hàng từ chối lệnh."""
    assert normalize_memo(raw) == expected


def test_payload_is_always_pure_ascii_whatever_the_memo() -> None:
    """Tầng QR chỉ mã hoá ASCII và NÉM khi gặp byte khác — đúng lúc người dùng bấm nút.

    Đây là bug đã có thật: `Đ` và `đ` là ký tự RIÊNG trong Unicode, không phải `D` cộng dấu,
    nên bước bỏ dấu theo NFD không đụng tới chúng và chúng lọt qua vòng lọc vì vẫn là chữ cái.
    """
    from nostalgia.auth.qr import encode_qr

    # Gạch ngang dài ở chuỗi cuối là CỐ Ý: đây là ký tự người ta hay dán từ Word vào, và nó
    # không phải chữ cái nên phải bị thay bằng khoảng trắng chứ không lọt xuống tầng QR.
    for memo in ("Đóng góp", "Ủng hộ Đặng", "Cảm ơn Đ.", "ủng hộ – nostalgia"):  # noqa: RUF001
        payload = vietqr_payload(ACCOUNT, memo)
        payload.encode("ascii")  # ném ngay tại đây nếu lọt ký tự ngoài ASCII
        encode_qr(payload)


def test_memo_that_normalizes_to_nothing_is_dropped_not_left_empty() -> None:
    """Thẻ 62 rỗng là thẻ sai cấu trúc; bỏ hẳn thẻ mới đúng."""
    assert "62" not in parse_tlv(vietqr_payload(ACCOUNT, "!!!"))


@pytest.mark.parametrize(
    "account",
    [
        BankAccount("97O436", "1234567890", "A"),  # chữ O thay số 0
        BankAccount("970436", "12345 67890", "A"),
        BankAccount("", "1234567890", "A"),
    ],
)
def test_rejects_accounts_that_are_not_all_digits(account: BankAccount) -> None:
    """Mã ngân hàng/số tài khoản lẫn chữ dựng ra mã QR mà app ngân hàng từ chối — chặn sớm,
    tại chỗ sửa được, thay vì để người dùng thấy một mã không quét được."""
    with pytest.raises(ValueError, match="chữ số"):
        vietqr_payload(account, MEMO)
