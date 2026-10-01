"""Trang tải ở `docs/site/`: HTML và JS phải khớp nhau, và mọi file nó trỏ tới phải có thật.

Vì sao đáng một file test dù trang chỉ là ba file tĩnh: nó là nơi DUY NHẤT người lạ gặp dự
án, và ba kiểu hỏng của nó đều im lặng. Đổi tên một `id` trong HTML thì `app.js` ném
`TypeError` ở dòng đầu và cả khối tải biến mất — trang vẫn ra, vẫn đẹp, chỉ là không tải
được gì. Đổi tên một ảnh chụp trong `docs/showcase/` thì chỗ đó thành ô trống. Và nếu class
`.reveal` bị viết thẳng vào HTML thì ai tắt JavaScript sẽ thấy một trang trắng vĩnh viễn.

Không có trình duyệt ở đây nên test này KHÔNG kiểm được hoạt ảnh chạy đúng hay không — phần
đó đã soi bằng ảnh chụp qua CDP. Nó chỉ gác những thứ đọc được từ văn bản.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parents[1] / "docs" / "site"
HTML = (SITE / "index.html").read_text(encoding="utf-8")
JS = (SITE / "app.js").read_text(encoding="utf-8")
CSS = (SITE / "style.css").read_text(encoding="utf-8")


def test_every_id_the_script_reaches_for_exists_in_the_page() -> None:
    """`getElementById` trả `null` cho id không có, và `null.textContent` ném ngay — cả khối
    tải chết, nhưng trang vẫn hiện đầy đủ phần còn lại nên nhìn bằng mắt không ra."""
    wanted = set(re.findall(r'getElementById\("([^"]+)"\)', JS))
    present = set(re.findall(r'id="([^"]+)"', HTML))
    assert wanted <= present, f"HTML thiếu id: {sorted(wanted - present)}"


def test_every_local_file_the_page_points_at_is_really_there() -> None:
    """Ảnh chụp sống ở `docs/showcase/`, ngoài thư mục trang. Đổi tên một file ở đó thì trang
    thủng một ô trống và không có gì báo."""
    refs = re.findall(r'(?:src|href)="(?!https?:|data:|#|mailto:)([^"]+)"', HTML)
    missing = [ref for ref in refs if not (SITE / ref).resolve().is_file()]
    assert not missing, f"trang trỏ tới file không có: {missing}"


def test_the_hidden_state_is_added_by_script_not_baked_into_the_html() -> None:
    """Class `.reveal` (opacity 0) phải do `app.js` GẮN VÀO, không viết sẵn trong HTML.

    Viết sẵn thì người tắt JavaScript — hoặc người bị chặn script bởi tiện ích — thấy một
    trang trắng trơn. Mất hoạt ảnh là chấp nhận được; mất nội dung thì không.
    """
    assert "classList.add" in JS and '"reveal"' in JS, "app.js không còn tự gắn .reveal"
    # Soi TỪNG class trong mỗi thuộc tính `class`, không phải tìm chuỗi `class="reveal`:
    # `class="steps-grid reveal"` cũng là viết cứng, mà cách tìm theo chuỗi thì bỏ lọt.
    # (Đã thử: bản gác theo chuỗi không đỏ khi gỡ vá.)
    for attribute in re.findall(r'class="([^"]*)"', HTML):
        assert "reveal" not in attribute.split(), (
            f'class .reveal viết cứng trong HTML (class="{attribute}") — tắt JS là trang trắng'
        )


def test_the_navbar_is_readable_even_with_no_script_at_all() -> None:
    """Nền thanh nav bật theo cuộn qua `.is-stuck` do JS gắn. Không JS thì nó trong suốt mãi
    và chữ của nó đè lên nội dung cuộn qua phía dưới — đọc không ra chữ nào.

    Vá bằng class `.no-js` đặt sẵn trên `<html>`, `app.js` gỡ ở dòng đầu. Test gác đủ ba
    mảnh: HTML đặt, JS gỡ, CSS dùng. Thiếu một mảnh là lỗi quay lại.
    """
    assert 'class="no-js"' in HTML, "<html> mất class no-js"
    assert 'classList.remove("no-js")' in JS, "app.js không gỡ no-js — nền nav hiện ngay trên hero"
    assert ".no-js .nav" in CSS, "CSS không còn nhánh nền cho trường hợp không có JavaScript"


def test_motion_is_switched_off_for_people_who_asked_for_that() -> None:
    """Hai lớp phải cùng tôn trọng `prefers-reduced-motion`: CSS tắt hoạt ảnh, JS không gắn
    parallax lẫn observer. Chỉ một trong hai thì người bật cờ vẫn lãnh nửa số hiệu ứng."""
    assert "prefers-reduced-motion" in CSS
    assert "prefers-reduced-motion" in JS


def test_the_theme_colours_match_the_launcher_exactly() -> None:
    """Bảng màu trang web chép từ `Theme.qml`. Lệch một mã là người tải về thấy một app khác
    với thứ vừa xem — và đó là kiểu lệch không ai phát hiện ra, vì hai thứ không bao giờ nằm
    cạnh nhau trên màn hình."""
    theme = (
        Path(__file__).resolve().parents[1] / "src" / "nostalgia" / "ui" / "qml" / "Theme.qml"
    ).read_text(encoding="utf-8")
    for name, value in (("bg", "#141821"), ("surface", "#1c212c"), ("grass", "#5ac54f")):
        assert f"--{name}: {value};" in CSS, f"CSS đổi màu {name}"
        assert value in theme, f"Theme.qml không còn {value} — một trong hai bên đã trôi"


@pytest.mark.parametrize("anchor", sorted(set(re.findall(r'href="#([^"]+)"', HTML))))
def test_every_in_page_link_lands_somewhere(anchor: str) -> None:
    """Liên kết `#...` trỏ vào hư vô thì bấm xong trang đứng im — trông y như nút hỏng."""
    assert f'id="{anchor}"' in HTML, f"neo #{anchor} không có đích"
