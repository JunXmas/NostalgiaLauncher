"""Mã QR ủng hộ: số tài khoản ghim trong kho, Worker đè được, mã vẽ bằng stdlib."""

from __future__ import annotations

import logging

from nostalgia.auth.qr import QrCode, encode_qr, qr_png_bytes
from nostalgia.donate.vietqr import BankAccount, vietqr_payload
from nostalgia.facade.context import LauncherContext
from nostalgia.model.json_value import JsonValue
from nostalgia.net.payload import fetch_json
from nostalgia.repo.endpoints import (
    DONATE_ACCOUNT_HOLDER,
    DONATE_ACCOUNT_NUMBER,
    DONATE_BANK_BIN,
    DONATE_BANK_NAME,
    DONATE_MEMO,
)

logger = logging.getLogger(__name__)

PINNED_ACCOUNT = BankAccount(
    DONATE_BANK_BIN, DONATE_ACCOUNT_NUMBER, DONATE_ACCOUNT_HOLDER, DONATE_BANK_NAME
)


class DonateOperations(LauncherContext):
    __slots__ = ()

    def donate_account(self) -> BankAccount | None:
        """Tài khoản GHIM trong kho. Không chạm mạng; `None` khi chưa khai số nào.

        Tách khỏi `refresh_donate_account` để giao diện dựng được mã QR ngay lúc mở trang,
        chưa phải đợi một request nào — đây là thứ luôn có, kể cả khi máy đang offline.
        """
        return PINNED_ACCOUNT if PINNED_ACCOUNT.bin and PINNED_ACCOUNT.number else None

    def refresh_donate_account(self) -> BankAccount | None:
        """CHẠM MẠNG. Số tài khoản hiện hành từ Worker; `None` nếu không lấy được.

        `None` nghĩa là "cứ dùng cái đang có", không phải lỗi cần hiện ra: đổi số tài khoản
        là chuyện hiếm, còn máy offline là chuyện thường. Ghi log mức `warning` vì cả bước
        này hỏng — im lặng ở đây nghĩa là một ngày nào đó tiền chảy vào tài khoản đã đóng mà
        không ai biết vì sao.
        """
        try:
            with self.make_http_client() as http_client:
                document = fetch_json(
                    http_client, self.endpoints.donate_account, what="số tài khoản ủng hộ"
                )
        except Exception:
            logger.warning("không lấy được số tài khoản ủng hộ từ máy chủ; dùng số ghim sẵn")
            logger.debug("chi tiết lỗi lấy số tài khoản ủng hộ", exc_info=True)
            return None
        return _account_from_json(document)

    def donate_qr(self, account: BankAccount | None = None, *, scale: int = 6) -> bytes | None:
        """PNG mã VietQR cho `account` (mặc định: tài khoản ghim). `None` khi chưa có tài khoản.

        Trả PNG chứ không trả đường dẫn file: mã dựng lại trong vài mili giây nên không đáng
        một file tạm phải dọn, và không có file tạm thì không có chuyện số tài khoản nằm lại
        trên đĩa sau khi đóng launcher.
        """
        chosen = self.donate_account() if account is None else account
        if chosen is None:
            return None
        return qr_png_bytes(self.donate_qr_code(chosen), scale=scale)

    @staticmethod
    def donate_qr_code(account: BankAccount) -> QrCode:
        """Lưới mã QR cho `account`, chưa vẽ ra ảnh — để test soi từng ô."""
        return encode_qr(vietqr_payload(account, DONATE_MEMO))

    @staticmethod
    def donate_memo() -> str:
        """Nội dung chuyển khoản mà mã QR điền sẵn — giao diện hiện ra để người dùng đối chiếu."""
        return DONATE_MEMO


def _account_from_json(document: JsonValue) -> BankAccount | None:
    """Đọc ba trường bắt buộc; thiếu hay sai kiểu thì coi như Worker không trả gì.

    Cố ý khắt khe: một tài khoản nửa vời (có số, thiếu mã ngân hàng) dựng ra mã QR mà app
    ngân hàng từ chối, tệ hơn hẳn việc lùi về số ghim sẵn vẫn quét được.
    """
    if not isinstance(document, dict):
        return None
    fields = [document.get(key) for key in ("bin", "number", "holder")]
    if not all(isinstance(value, str) and value.strip() for value in fields):
        logger.warning("máy chủ trả số tài khoản ủng hộ thiếu trường; dùng số ghim sẵn")
        return None
    bank_bin, number, holder = (str(value).strip() for value in fields)
    # `bank` KHÔNG bắt buộc: nó chỉ là dòng chữ người quét đọc, thiếu thì bớt một dòng chứ
    # không làm mã sai. Bắt buộc nó là tự tạo thêm một đường để cả câu trả lời bị từ chối.
    bank = document.get("bank")
    return BankAccount(bank_bin, number, holder, bank.strip() if isinstance(bank, str) else "")
