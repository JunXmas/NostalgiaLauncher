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


def test_there_is_still_a_download_button_with_no_script() -> None:
    """Nút tải chính do `app.js` dựng sau khi hỏi API GitHub. Không có JS thì nó không bao giờ
    hiện, và khối tải đứng mãi ở dòng "Đang dò bản mới nhất…" — một hộp không có lối ra.

    Đây là trang TẢI XUỐNG: mất hoạt ảnh thì thôi, mất đường tải thì trang mất lý do tồn tại.
    `<noscript>` dựng một nút tĩnh trỏ về `releases/latest`.
    """
    assert "<noscript>" in HTML, "mất lối tải tĩnh cho người không chạy được JavaScript"
    block = HTML[HTML.index("<noscript>") : HTML.index("</noscript>")]
    assert "releases/latest" in block, "nút dự phòng không trỏ tới bản phát hành mới nhất"


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


def test_the_glass_surfaces_have_something_behind_them_to_blur() -> None:
    """`backdrop-filter` trên một nền tối trơn không làm ra kính, nó làm ra một ô xám mờ.

    Thứ cứu nó là lớp quầng màu `fixed` sau toàn trang (`body::before`): tấm kính trôi qua
    trên một bầu trời đứng yên, và đó là lúc độ mờ thật sự đổi hình. Gỡ lớp quầng đi thì
    trang vẫn chạy, vẫn không báo lỗi gì — chỉ là mất sạch chất vật liệu. Đúng kiểu hỏng
    không ai phát hiện ra.
    """
    assert "body::before" in CSS, "mất lớp quầng màu sau trang — kính không còn gì để làm mờ"
    assert "position: fixed" in CSS, "lớp quầng phải `fixed`; cuộn theo trang thì độ mờ đứng yên"
    assert "backdrop-filter" in CSS, "không còn bề mặt nào làm mờ nền"
    # Mép bắt sáng: thứ phân biệt "tấm vật liệu" với "vùng màu". Thiếu nó thì kính dán phẳng.
    assert "--glass-edge" in CSS and "inset 0 1px 0" in CSS, "mép kính mất đường bắt sáng"


def test_the_moving_shine_is_also_switched_off_for_reduced_motion() -> None:
    """Vệt sáng quét ngang nút chính là CHUYỂN ĐỘNG, không phải màu.

    Dễ bỏ sót vì nó nằm trong `::after` chứ không phải trong danh sách `.reveal`/`.rise` —
    tắt hết hoạt ảnh kia rồi mà vẫn còn một thứ chạy trên màn hình của người bật cờ.
    """
    still = CSS[CSS.index("prefers-reduced-motion") :]
    assert ".btn-primary::after" in still, "vệt sáng quét nút vẫn chạy khi người dùng xin tắt"


def test_the_license_on_the_page_matches_the_one_in_the_repo() -> None:
    """Trang từng ghi GPL-3.0 trong khi kho là AGPL-3.0 — khác hẳn nghĩa pháp lý (AGPL buộc
    mở mã cả khi chỉ chạy làm dịch vụ mạng). Ghi sai giấy phép của chính mình là thứ phá uy
    tín nhanh nhất, và không có test nào khác trong kho này đọc tới nó."""
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert "AGPL-3.0-only" in pyproject, "pyproject đổi giấy phép — cập nhật cả trang web"
    assert "AGPL-3.0" in HTML, "trang web ghi sai giấy phép"
    assert not re.search(r"(?<!A)GPL-3\.0", HTML), "trang web còn chỗ ghi GPL-3.0 (thiếu chữ A)"


def test_the_numbers_in_the_proof_band_are_not_invented() -> None:
    """Băng chỉ tiêu là chỗ trang doanh nghiệp đặt logo khách hàng. Dự án này thay bằng số về
    mã nguồn — nên mỗi số phải đếm lại được từ chính kho, không thì nó chỉ là logo bịa dưới
    dạng chữ số.

    Hai số kiểm thẳng: `0` phụ thuộc runtime đối chiếu `dependencies = []`, và số test đối
    chiếu số hàm `def test_`. Ngưỡng là một KHOẢNG chứ không phải con số chính xác: pytest
    đếm cả bản sinh ra từ `parametrize` nên luôn nhiều hơn số hàm, và ghim cứng thì mỗi lần
    thêm một test lại đỏ một test khác.
    """
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert "dependencies = []" in pyproject, "lõi đã có phụ thuộc runtime — số 0 trên trang sai"

    tests_dir = Path(__file__).resolve().parent
    functions = sum(
        len(re.findall(r"^def test_", path.read_text(encoding="utf-8"), re.MULTILINE))
        for path in tests_dir.rglob("test_*.py")
    )
    found = re.search(r'class="proof-num">([^<]+)<', HTML)
    assert found is not None, "băng chỉ tiêu mất ô đầu — không còn số test để đối chiếu"
    claimed = int(re.sub(r"\D", "", found.group(1)))
    assert functions <= claimed <= functions * 3, (
        f"trang khoe {claimed} test mà kho có {functions} hàm test — số đã trôi"
    )
