"""Trang TÀI KHOẢN với tài khoản Microsoft: hàng nút Làm mới / Tải skin / Slim hiện ra mà
không kéo theo vòng lặp bố cục.

Lỗi thật: `CheckRow` lấy bề rộng theo cha, đặt trong một `Row` (Row rộng theo con) → Qt cảnh
báo "possible QQuickItem::polish() loop" 1.280 lần trong một phiên, CPU quay không, và người
dùng thấy trang "lag". Harness với tài khoản ngoại tuyến không thấy vì hàng nút đó ẩn.
"""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from PySide6.QtCore import QObject, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from qml_tree import find_item
from test_qml import make_launcher

from nostalgia.account.model import ELY, MICROSOFT
from nostalgia.account.offline import build_offline_account
from nostalgia.account.store import save_accounts
from nostalgia.api import Launcher
from nostalgia.ui.app import build_view

pytestmark = pytest.mark.usefixtures("qt_app")


def test_microsoft_account_row_does_not_loop_the_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(tmp_path)
    premium = replace(build_offline_account("JunSlayest"), account_kind=MICROSOFT)
    save_accounts(launcher.paths.accounts_json, (premium,))
    # Tài khoản Microsoft chưa có skin trong cache thì cầu nối tự tải — test không chạm mạng.
    monkeypatch.setattr(Launcher, "refresh_skin", Launcher.describe_skin)

    warnings: list[str] = []
    qInstallMessageHandler(lambda _kind, _context, message: warnings.append(message))
    try:
        view, _bridge = build_view(launcher)
        view.show()
        root_item = view.rootObject()
        assert root_item is not None
        sidebar = root_item.findChild(QObject, "sidebar")
        assert sidebar is not None
        sidebar.setProperty("currentIndex", 3)
        deadline = time.monotonic() + 0.6
        while time.monotonic() < deadline:
            QGuiApplication.processEvents()
            time.sleep(0.01)
    finally:
        qInstallMessageHandler(None)

    loops = [message for message in warnings if "polish" in message]
    assert loops == [], f"vòng lặp bố cục: {loops[0]}"
    assert warnings == []


def _ely_account_detail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Dựng trang TÀI KHOẢN với đúng một tài khoản Ely, trả về dòng chữ nhỏ dưới tên."""
    launcher = make_launcher(tmp_path)
    save_accounts(
        launcher.paths.accounts_json,
        (replace(build_offline_account("JunSlayest"), account_kind=ELY),),
    )
    monkeypatch.setattr(Launcher, "refresh_skin", Launcher.describe_skin)
    view, _bridge = build_view(launcher)
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", 3)
    QGuiApplication.processEvents()
    detail = find_item(root_item, "accountDetail")
    assert detail is not None
    return str(detail.property("text"))


def test_ely_row_says_when_skins_cannot_show_in_game_yet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Skin Ely cần authlib-injector — javaagent JVM, KHÔNG phải mod: launcher tự tải, tự tiêm,
    người dùng không bấm gì. Nhưng "tự động" mà im lặng thì lúc nó hỏng họ chỉ thấy skin biến
    mất và không có chỗ nào để nhìn. Chưa có jar thì hàng tài khoản phải nói ra."""
    assert "đang tải hỗ trợ" in _ely_account_detail(tmp_path, monkeypatch)


def test_ely_row_goes_back_to_the_uuid_once_support_is_there(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Có jar rồi thì không còn gì để báo — trả chỗ đó lại cho dòng UUID."""
    (tmp_path / "data" / "authlib-injector").mkdir(parents=True)
    (tmp_path / "data" / "authlib-injector" / "authlib-injector-9.9.9.jar").write_bytes(b"PK")
    assert "đang tải hỗ trợ" not in _ely_account_detail(tmp_path, monkeypatch)


def _accounts_page_at(
    width: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> QQuickItem:
    launcher = make_launcher(tmp_path)
    save_accounts(
        launcher.paths.accounts_json,
        (
            replace(build_offline_account("JunSlayest"), account_kind=MICROSOFT),
            replace(build_offline_account("JunEly"), account_kind=ELY),
        ),
    )
    monkeypatch.setattr(Launcher, "refresh_skin", Launcher.describe_skin)
    view, _bridge = build_view(launcher)
    view.resize(width, 768)
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", 3)
    QGuiApplication.processEvents()
    return root_item


@pytest.mark.parametrize("width", [1366, 1920])
def test_add_skin_button_stays_inside_its_panel(
    width: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nút "Thêm skin" từng lọt ra ngoài mép phải ô Skin: hàng tiêu đề dùng một `Item` đệm
    rộng `header.width - 330`, con số chỉ đúng ở đúng một bề rộng cửa sổ. Neo nút vào mép
    phải thì mọi bề rộng đều đúng — nên test đo ở hai bề rộng."""
    root_item = _accounts_page_at(width, tmp_path, monkeypatch)
    button = find_item(root_item, "importSkinButton")
    assert button is not None

    panel = find_item(root_item, "skinPanel")
    assert panel is not None

    right_edge = button.mapToItem(root_item, button.width(), 0).x()
    panel_right = panel.mapToItem(root_item, panel.width(), 0).x()

    assert right_edge <= panel_right, (
        f"nút tràn {right_edge - panel_right:.0f} px ra ngoài ô Skin ở bề rộng {width}"
    )


def test_every_inactive_account_offers_a_way_to_switch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bấm cả hàng vẫn chuyển được, nhưng không ai đoán ra: hàng không trông giống nút và
    dấu ✓ chỉ nói hàng NÀO đang dùng, không nói làm sao đổi sang hàng khác."""
    root_item = _accounts_page_at(1366, tmp_path, monkeypatch)
    buttons: list[QQuickItem] = []
    _collect(root_item, "useAccountButton", buttons)

    assert len(buttons) == 2, "mỗi hàng tài khoản phải có một nút Dùng"


def _collect(node: QQuickItem, name: str, found: list[QQuickItem]) -> None:
    """Như `find_item` nhưng gom hết. Phải đi `childItems()` chứ không đi cây QObject: delegate
    của `ListView` không có cha QObject nên `children()` không thấy hàng tài khoản nào."""
    if node.objectName() == name:
        found.append(node)
    for child in node.childItems():
        _collect(child, name, found)


def test_the_use_button_never_appears_under_the_cursor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nút Dùng nằm đè lên vùng hover của hàng. Cho nó `visible` theo hover thì nó hiện ra
    ngay dưới con trỏ — một item vừa xuất hiện dưới con trỏ là một lần tính lại hover, và
    mắt thấy nút chớp. Nên nút phải LUÔN nằm trong cây, chỉ mờ đi bằng `opacity`."""
    root_item = _accounts_page_at(1366, tmp_path, monkeypatch)
    buttons: list[QQuickItem] = []
    _collect(root_item, "useAccountButton", buttons)
    assert buttons, "không tìm thấy nút Dùng nào"

    for button in buttons:
        assert button.isVisible() is True, "nút Dùng bật/tắt bằng visible — sẽ chớp khi trỏ vào"
        assert button.opacity() == 0.0, "chưa trỏ vào hàng nào thì nút phải trong suốt"


def test_ely_account_gets_a_link_to_change_its_real_skin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Đổi skin THẬT của tài khoản Ely chỉ làm được ở ely.by — launcher không có API upload
    cho họ (khác Microsoft, có). Không có nút này thì họ đổi trong thư viện, thấy nhân vật đổi
    ngay trước mắt, và tưởng người chơi khác trong game cũng thấy."""
    root_item = _accounts_page_at(1366, tmp_path, monkeypatch)
    link = find_item(root_item, "elySkinSiteButton")
    assert link is not None

    # Đang chọn JunSlayest (microsoft): nút phải ẩn, vì Microsoft upload thẳng được.
    assert link.isVisible() is False

    page = find_item(root_item, "accountsPage")
    assert page is not None
    page.setProperty("shownName", "JunEly")
    QGuiApplication.processEvents()

    assert link.isVisible() is True, "tài khoản Ely phải có đường ra ely.by để đổi skin thật"


def test_ely_sign_in_offers_a_way_to_get_an_account(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hộp đăng nhập Ely chỉ có ô email + mật khẩu: người chưa có tài khoản đứng đó không biết
    lấy đâu ra. Đăng ký phải mở trình duyệt — ely.by đòi xác nhận email, dựng form trong
    launcher chỉ là một chỗ nữa cho mật khẩu đi qua tay ta."""
    root_item = _accounts_page_at(1366, tmp_path, monkeypatch)
    dialog = find_item(root_item, "addAccountDialog")
    assert dialog is not None
    register = find_item(root_item, "elyRegisterButton")
    assert register is not None

    dialog.setProperty("visible", True)
    dialog.setProperty("mode", "ely")
    QGuiApplication.processEvents()

    assert register.isVisible() is True, "nhánh Ely phải có nút đăng ký cạnh nút đăng nhập"


def test_ely_links_point_at_the_account_site_not_the_skin_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ely.by` là catalog skin của người khác; mọi thứ tài khoản nằm ở `account.ely.by`.
    Đoán sai một lần rồi: `ely.by/register` trả 404 ngay trước mặt jun. Không chạm mạng —
    chỉ gác cái tên miền, vì đó mới là chỗ đã sai."""
    root_item = _accounts_page_at(1366, tmp_path, monkeypatch)
    for name in ("elyRegisterButton", "elySkinSiteButton"):
        button = find_item(root_item, name)
        assert button is not None
        target = button.property("target").toString()
        assert target.startswith("https://account.ely.by/"), f"{name} trỏ sai chỗ: {target}"
