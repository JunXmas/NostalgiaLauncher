"""Font đóng kèm: có mặt, nạp được, và phủ đủ dấu tiếng Việt.

Đây là loại lỗi không bao giờ làm test khác đỏ. Thiếu một file font thì Qt lặng lẽ rơi về
font hệ thống, giao diện vẫn dựng, mọi test vẫn xanh — chỉ có người dùng thấy chữ khác đi,
và trên máy thiếu dấu tiếng Việt thì chữ nhảy font giữa câu.
"""

from __future__ import annotations

import re

import pytest

from nostalgia.ui.app import QML_DIR, SANS_FAMILY, load_fonts

pytestmark = pytest.mark.usefixtures("qt_app")

FONTS_DIR = QML_DIR / "assets" / "fonts"

# Đủ để bắt lỗi thật: mỗi nguyên âm mang dấu một kiểu, cộng đ/ơ/ư là những chữ mà font
# phương Tây hay thiếu nhất.
VIETNAMESE = "ăâđêôơưĂÂĐÊÔƠƯáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"


def test_font_files_are_present() -> None:
    """Thiếu file là mất diện mạo — và mất lặng lẽ, nên phải bắt ở đây."""
    missing = [
        name
        for name in ("Inter-Regular.ttf", "Inter-Medium.ttf",
                     "Inter-SemiBold.ttf", "MinecraftF2D.otf")
        if not (FONTS_DIR / name).is_file()
    ]
    assert not missing, f"thiếu file font: {missing}"


def test_every_bundled_font_ships_its_licence() -> None:
    """Cả hai họ font đều là OFL 1.1, giấy phép này BẮT BUỘC phát hành kèm bản quyền."""
    licences = list(FONTS_DIR.glob("*-OFL.txt"))
    assert len(licences) >= 2, f"chỉ thấy {len(licences)} file giấy phép"
    for path in licences:
        assert "SIL OPEN FONT LICENSE" in path.read_text(encoding="utf-8")


def test_every_bundled_font_covers_vietnamese() -> None:
    """Mỗi font đóng kèm phải vẽ được mọi ký tự có dấu.

    Đo bằng chính máy vẽ của Qt chứ không đọc bảng cmap bằng thư viện khác: thứ quan trọng
    là Qt có glyph để vẽ hay không, không phải file có khai báo hay không.
    """
    from PySide6.QtGui import QRawFont

    for path in sorted(FONTS_DIR.glob("*.[ot]tf")):
        raw = QRawFont(str(path), 16.0)
        missing = [c for c in VIETNAMESE if not raw.supportsCharacter(ord(c))]
        assert not missing, f"{path.name} thiếu {len(missing)} dấu: {''.join(missing[:12])}"


def test_loading_fonts_registers_the_sans_family() -> None:
    """Sau `load_fonts()`, họ chữ đọc phải thật sự có trong bảng font của Qt."""
    from PySide6.QtGui import QFontDatabase

    load_fonts()
    assert SANS_FAMILY in QFontDatabase.families()


def test_theme_and_python_agree_on_the_sans_family() -> None:
    """`Theme.sans` và `SANS_FAMILY` phải là cùng một chuỗi.

    Hai chỗ khai cùng một tên font là hai chỗ để quên. Lệch nhau thì QML xin một họ không ai
    nạp, Qt trả về font hệ thống, và không có gì báo lỗi.
    """
    theme = (QML_DIR / "Theme.qml").read_text(encoding="utf-8")
    found = re.search(r'property string sans:\s*"([^"]+)"', theme)
    assert found, "không tìm thấy `property string sans` trong Theme.qml"
    assert found.group(1) == SANS_FAMILY


def test_no_qml_file_hard_codes_a_font_size() -> None:
    """Cỡ chữ phải xin từ `Theme.font*`, không viết số vào từng file.

    Đây là nguyên nhân đo được của chuyện "các tab nhìn không giống nhau": trước khi gom,
    57 file QML rải tay 16 cỡ khác nhau cho vài vai trò — mỗi trang viết ở một thời điểm nên
    nhặt một cỡ riêng. Không có test này thì file thứ 58 lại viết `font.pixelSize: 13`.
    """
    offenders = [
        f"{path.relative_to(QML_DIR)}:{number}"
        for path in sorted(QML_DIR.rglob("*.qml"))
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"font\.pixelSize:\s*\d", line)
    ]
    assert not offenders, "cỡ chữ viết tay, phải dùng Theme.font*:\n" + "\n".join(offenders)


def test_theme_has_one_accent_per_sidebar_entry() -> None:
    """Bảng `Theme.accents` phải có đúng bằng số mục ở thanh bên.

    Màu nhấn nay tra theo chỉ số tab. Thêm một mục vào Sidebar mà quên thêm màu thì mục mới
    lặng lẽ mượn màu của mục cuối — `Math.min` trong Theme.qml giữ cho nó không crash, nên
    không có gì báo lỗi, chỉ có hai tab trùng sắc. Bớt một mục thì thừa một màu chết.
    """
    theme = (QML_DIR / "Theme.qml").read_text(encoding="utf-8")
    block = re.search(r"property var accents:\s*\[(.*?)\]", theme, re.S)
    assert block, "không tìm thấy `property var accents` trong Theme.qml"
    accents = re.findall(r'"#[0-9a-fA-F]{6}"', block.group(1))

    sidebar = (QML_DIR / "Sidebar.qml").read_text(encoding="utf-8")
    entries = re.findall(r"\{\s*label:\s*Tr\.text\(", sidebar)

    assert len(accents) == len(entries), (
        f"{len(accents)} màu nhấn cho {len(entries)} mục thanh bên"
    )


def test_accents_are_all_distinct() -> None:
    """Hai tab cùng màu thì màu hết là chỉ dẫn — đó là toàn bộ lý do có bảng này."""
    theme = (QML_DIR / "Theme.qml").read_text(encoding="utf-8")
    block = re.search(r"property var accents:\s*\[(.*?)\]", theme, re.S)
    assert block
    accents = [c.lower() for c in re.findall(r'"#[0-9a-fA-F]{6}"', block.group(1))]
    duplicates = {c for c in accents if accents.count(c) > 1}
    assert not duplicates, f"màu nhấn trùng nhau: {duplicates}"


def test_theme_pixel_family_matches_the_bundled_file() -> None:
    """`Theme.pixel` phải khớp tên họ THẬT bên trong file .otf, không phải tên file.

    Tên họ nằm trong bảng `name` của font và không liên quan gì tới tên file — đặt sai thì
    nhãn rơi về font thường mà không có cảnh báo nào.
    """
    from PySide6.QtGui import QFontDatabase

    font_id = QFontDatabase.addApplicationFont(str(FONTS_DIR / "MinecraftF2D.otf"))
    assert font_id >= 0, "không nạp được MinecraftF2D.otf"
    families = QFontDatabase.applicationFontFamilies(font_id)

    theme = (QML_DIR / "Theme.qml").read_text(encoding="utf-8")
    found = re.search(r'property string pixel:\s*"([^"]+)"', theme)
    assert found, "không tìm thấy `property string pixel` trong Theme.qml"
    assert found.group(1) in families, f"Theme.pixel={found.group(1)!r} không có trong {families}"
