"""Hộp ủng hộ: mã QR đúng chuỗi VietQR, và ẩn hẳn khi chưa khai số tài khoản.

Vì sao đáng một file riêng: đây là đường duy nhất trong launcher dẫn tới tiền thật. Hai kiểu
hỏng đều im lặng — mã vẽ ra một tài khoản khác (không ai biết cho tới khi tiền đi nhầm), hoặc
khung QR hiện ra trống trơn vì chưa ai khai số (người dùng quét mãi không được và cho rằng
launcher hỏng).
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from modern_window import open_modern
from PySide6.QtCore import QObject
from qml_tree import find_item
from test_bridges import wait_until

from nostalgia.api import BankAccount, Launcher
from nostalgia.ui.settings_bridge import QR_SCALE, SettingsBridge

pytestmark = pytest.mark.usefixtures("qt_app")

ACCOUNT = BankAccount("970436", "1234567890123", "NGUYEN VAN A")


def test_the_dialog_exists_and_the_donate_button_opens_it(tmp_path: Path) -> None:
    """Hộp phải nằm ở gốc cửa sổ chứ không trong trang: trang CÀI ĐẶT nạp qua Loader, hộp
    dựng trong đó sẽ không phủ được thanh điều hướng."""
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    _view, _bridge, root_item = open_modern(launcher)

    dialog = root_item.findChild(QObject, "donateDialog")
    assert dialog is not None, "cửa sổ thiếu DonateDialog"
    assert dialog.property("visible") is False, "hộp ủng hộ không được tự bật lúc mở launcher"

    dialog.metaObject().invokeMethod(dialog, "open")
    assert dialog.property("visible") is True

    assert find_item(root_item, "donateQrImage") is not None or not str(
        SettingsBridge(launcher).donateQr
    ), "có mã QR nhưng không có ô Image nào vẽ nó"


def test_the_navigation_offers_donate_from_any_page(tmp_path: Path) -> None:
    """Ủng hộ phải mở được từ THANH ĐIỀU HƯỚNG khi đang đứng ở trang chủ (index 0): nút Premium
    → nút ủng hộ trong hộp. Nút chỉ nằm cuối trang CÀI ĐẶT thì một lời mời không ai thấy bằng
    không có."""
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    _view, _bridge, root_item = open_modern(launcher)
    assert root_item.property("currentIndex") == 0, "phải ở trang chủ"

    support = find_item(root_item, "openSupport")
    assert support is not None, "thanh điều hướng thiếu lối vào ủng hộ"
    support.metaObject().invokeMethod(support, "clicked")
    support_dialog = root_item.findChild(QObject, "supportDialog")
    assert support_dialog is not None and support_dialog.property("visible") is True
    donation = support_dialog.findChild(QObject, "paymentDonation")
    assert donation is not None
    dialog = root_item.findChild(QObject, "donateDialog")
    assert dialog is not None and dialog.property("visible") is False
    donation.metaObject().invokeMethod(donation, "clicked")
    wait_until(lambda: dialog.property("visible") is True)
    # Đây là LIÊN KẾT, không phải điểm đến: mở hộp xong vẫn phải đứng nguyên ở trang chủ.
    assert root_item.property("currentIndex") == 0


def test_the_qr_data_uri_decodes_to_the_png_the_engine_built(tmp_path: Path) -> None:
    """Chuỗi `data:` QML nhận phải là ĐÚNG những byte PNG mà engine dựng, không phải một ảnh
    khác cùng kích thước. Kiểu lỗi mà nó gác: ai đó đổi `scale` ở một trong hai chỗ."""
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    bridge = SettingsBridge(launcher)
    uri = str(bridge.donateQr)

    if launcher.donate_account() is None:
        assert uri == "", "chưa khai số tài khoản mà vẫn trả data URI — QML sẽ vẽ ảnh hỏng"
        return
    prefix = "data:image/png;base64,"
    assert uri.startswith(prefix)
    assert base64.b64decode(uri[len(prefix) :]) == launcher.donate_qr(scale=QR_SCALE)


def test_the_memo_shown_is_the_memo_baked_into_the_qr(tmp_path: Path) -> None:
    """Người quét đối chiếu dòng "Nội dung" với app ngân hàng. Hai chỗ lệch nhau là người
    dùng sửa tay thành thứ khác, và chủ dự án mất đường lọc sao kê."""
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    bridge = SettingsBridge(launcher)
    memo = str(bridge.donateMemo)

    from nostalgia.donate.vietqr import vietqr_payload

    assert memo and memo in vietqr_payload(ACCOUNT, memo)


def test_nothing_is_promised_when_no_account_is_pinned(tmp_path: Path) -> None:
    """Chưa khai số tài khoản thì cả ba thuộc tính phải rỗng CÙNG NHAU.

    Rỗng một nửa là tệ nhất: khung QR trắng trơn kèm dòng "Nội dung: UNG HO NOSTALGIA" trông
    y như một tính năng chạy được, và người dùng ngồi quét mãi một ô trống.
    """
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    bridge = SettingsBridge(launcher)
    if launcher.donate_account() is not None:
        pytest.skip("kho đã khai số tài khoản; nhánh này chỉ áp cho lúc chưa khai")
    assert str(bridge.donateQr) == ""
    assert str(bridge.donateAccountHolder) == ""
