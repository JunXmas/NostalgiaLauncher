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

from site_sources import CSS, HTML, JS, PAGES_BASE, REPO, SITE, strip_js_comments


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


def test_the_stylesheet_does_not_ask_for_a_file_that_was_deleted() -> None:
    """`url()` trong CSS là điểm mù của test trên — nó chỉ đọc `src`/`href` trong HTML.

    Khi gỡ `hero.jpg` đi, nếu sót lại một `url("hero.jpg")` thì trình duyệt tải 404 rồi vẽ
    một mảng trống: không lỗi, không cảnh báo, chỉ là hero mất nền. Đúng kiểu hỏng im lặng
    mà cả bộ test còn lại không với tới.
    """
    refs = re.findall(r'url\(["\']?(?!https?:|data:|#)([^"\')]+)["\']?\)', CSS)
    missing = [ref for ref in refs if not (SITE / ref).resolve().is_file()]
    assert not missing, f"CSS trỏ tới file không có: {missing}"


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


def test_the_page_backdrop_is_not_painted_over_by_an_opaque_body() -> None:
    """Lỗi im lặng đã sống suốt mấy bản, và chính là nguyên nhân gốc của "không ra kính".

    `html` và `body` cùng khai `background: var(--bg)`. Khi `html` ĐÃ có nền, trình duyệt
    không còn đẩy nền của `body` lên canvas nữa mà vẽ nó thành một hộp đục của riêng `body`
    — và hộp đục ấy phủ kín mọi `::before`/`::after` đặt ở `z-index: -1` của chính `body`.
    Tức là lớp quầng màu nền, thứ duy nhất cho `backdrop-filter` có việc để làm, đã bị che
    hoàn toàn. Trang vẫn chạy, không một cảnh báo, chỉ là mọi tấm kính đọc ra ô xám.

    Không test nào cũ bắt được: `body::before` vẫn có mặt trong file, `position: fixed` vẫn
    đúng, `backdrop-filter` vẫn đúng. Mọi khẳng định đều xanh trong khi màn hình thì sai.
    """
    body = CSS[CSS.index("\nbody {") : CSS.index("body::before")]
    assert "background:" not in body, (
        "`body` có nền đục trong khi `html` cũng có — nền này sẽ phủ kín lớp quầng "
        "`body::before`/`body::after` và mọi tấm kính mất thứ để làm mờ"
    )
    assert "background: var(--bg)" in CSS[: CSS.index("\nbody {")], (
        "nền trang phải nằm ở `html`, nếu không trang hở ra màu trắng mặc định"
    )


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


def test_the_download_counter_still_reads_a_real_number_when_the_api_is_silent() -> None:
    """Con số lượt tải là thứ DUY NHẤT trên trang đổi sau mỗi lượt tải, nên cũng là thứ duy
    nhất lặng lẽ sai được. Ba cách nó hỏng mà chủ trang không thấy:

    - Để trống rồi chờ JS điền: người tắt script, và người gặp lúc API GitHub cháy ngưỡng
      60 lượt/giờ/IP (ký túc xá, quán net, NAT nhà mạng dùng chung một IP), đọc ra một ô
      rỗng giữa băng bốn số liệu — trang hỏng chứ không phải số chưa tải xong.
    - Điền `0` khi API im: số 0 đọc ra "chưa ai tải", tức nói dối về chính thứ đang quảng cáo.
    - Cộng cả `SHA256SUMS`: người cẩn thận tải thêm file băm để đối chiếu sẽ bị đếm hai lượt,
      con số phồng lên mà không ai kiểm lại được.

    Gác ở MÃ ĐÃ LỌC CHÚ THÍCH: mọi điều kiện ở đây đều được nhắc tên trong chính chú thích
    giải thích nó, nên soi nguyên file thì gỡ vá ra test vẫn xanh. Đã trả giá một lần.
    """
    # `[^<]*` chứ không `[^<]+`: ô RỖNG là đúng cái hỏng cần bắt, mà `+` không khớp nổi nội
    # dung rỗng nên nó rơi xuống `found is None` và báo "mất ô" — đúng màu, sai thông điệp.
    found = re.search(r'id="download-total"[^>]*>([^<]*)<', HTML)
    assert found is not None, "mất ô lượt tải trong băng chỉ tiêu"
    static = int(re.sub(r"\D", "", found.group(1)) or 0)
    assert static > 0, (
        f"ô lượt tải viết sẵn {found.group(1)!r} — người không có JavaScript và người gặp lúc "
        f"API cháy ngưỡng sẽ đọc ra một ô trống hoặc số 0"
    )

    code = strip_js_comments(JS)
    # Chỉ soi THÂN hàm đếm, không soi nguyên file: `SHA256SUMS` còn xuất hiện trong
    # `renderOtherFiles` (nó cũng loại file băm khỏi danh sách "file khác"), nên soi nguyên
    # file thì gỡ phép loại khỏi hàm đếm ra test vẫn xanh. Đã đo bằng gỡ vá, không đoán.
    counter = re.search(r"function countDownloads\(.*?\n\}", code, re.S)
    assert counter is not None, "mất hàm `countDownloads` — con số sẽ đứng im mãi"
    body = counter.group(0)
    assert "SHA256SUMS" in body, "không loại `SHA256SUMS` — một người tải bị đếm thành hai lượt"
    assert "download_count" in body, "không đọc `download_count` — con số sẽ đứng im mãi"
    # Phải để NGUYÊN số tĩnh khi tổng ra 0, không ghi đè. `total <= 0` là cách duy nhất phân
    # biệt "API im" với "thật sự chưa ai tải" ở phía trình duyệt.
    assert "total <= 0" in code, "không chặn ghi đè bằng 0 — API im sẽ xoá mất số thật"

    # Đúng MỘT lần gọi API: ngưỡng ẩn danh là 60 lượt/giờ/IP và cái hỏng khi cháy ngưỡng là
    # NÚT TẢI, không phải con số trang trí. Thêm một `fetch` nữa chỉ để đếm là tự chia đôi
    # ngưỡng đó cho mọi người dùng chung IP.
    assert code.count("fetch(") == 1, (
        f"có {code.count('fetch(')} lời gọi fetch — ngưỡng API ẩn danh 60 lượt/giờ/IP, "
        f"cháy ngưỡng thì nút tải chết chứ không phải con số"
    )

    # `/releases` trả về cả bản nháp và bản thử nghiệm, khác `/releases/latest`. Không lọc thì
    # một bản nháp — chỉ chủ kho thấy — thành "bản mới nhất", và asset của nó người lạ tải 404.
    assert ".draft" in code and ".prerelease" in code, (
        "không lọc bản nháp/thử nghiệm khỏi `/releases` — nút tải sẽ trỏ vào asset 404"
    )
    assert "published_at" in code, (
        "chọn bản mới nhất theo thứ tự API (`created_at`) chứ không theo `published_at` — "
        "kho này dựng bản DRAFT rồi publish tay nên hai mốc đó lệch nhau"
    )


def test_the_brand_mark_is_the_real_app_logo_not_an_svg_redrawn_to_look_like_it() -> None:
    """Trang từng dùng một `<symbol id="icon-grass">` vẽ tay ba hình chữ nhật cho giống khối
    lá. Nó "trông na ná" nên không ai thấy sai — mà người dùng thì nối trang web với app
    bằng đúng cái hình đó. Khác hình nghĩa là họ không chắc file vừa tải có phải thứ họ xem.

    Gác hai chiều vì mỗi chiều hỏng im lặng theo cách riêng: thiếu `<img>` thì có thể đã âm
    thầm quay về SVG vẽ tay, còn `icon-grass` quay lại thì nghĩa là có hai nhãn hiệu song
    song trong cùng một trang.
    """
    assert 'class="brand-logo" src="logo.webp"' in HTML, (
        "nhãn hiệu không còn dùng logo thật `logo.webp` — nếu đã thay bằng SVG vẽ lại thì "
        "nó không còn khớp icon ứng dụng"
    )
    assert HTML.count('class="brand-logo"') == 2, "phải đúng hai chỗ: nav và chân trang"
    assert "icon-grass" not in HTML, "khối lá vẽ tay đã quay lại — dùng `logo.webp` thay"

    # `width`/`height` phải khai trong HTML, nếu không trình duyệt không giữ chỗ trước khi ảnh
    # về và nav giật một nhịp khi tải (CLS).
    assert HTML.count('class="brand-logo" src="logo.webp" alt="" width="128" height="128"') == 2, (
        "thẻ logo thiếu `width`/`height` khai sẵn, hoặc `alt` không rỗng (cạnh nó đã có chữ "
        "'Nostalgia' nên trình đọc màn hình sẽ đọc tên hai lần)"
    )

    logo = SITE / "logo.webp"
    assert logo.is_file(), "thiếu `docs/site/logo.webp`"
    # 128px là gấp đôi cỡ hiển thị lớn nhất (34px ở nav) nên dư cho màn hình mật độ cao;
    # vượt 40 KB thì nghĩa là ai đó đã chép thẳng file gốc 256px vào đây.
    assert logo.stat().st_size < 40_000, f"`logo.webp` phình lên {logo.stat().st_size} byte"


def test_the_favicon_is_byte_for_byte_the_icon_the_installed_app_uses() -> None:
    """So THEO BYTE chứ không chỉ kiểm tồn tại.

    Đây là một file CHÉP, nên nó trôi theo đúng kiểu không ai nhận ra: đổi icon ứng dụng ở
    `packaging/icons/` thì bản chép trong `docs/site/` vẫn nằm im, vẫn hiện ra, vẫn là một
    hình hợp lệ — chỉ là tab trình duyệt và thanh tác vụ từ đó trở đi là hai hình khác nhau.
    """
    repo = Path(__file__).resolve().parents[1]
    source = repo / "packaging" / "icons" / "nostalgia-32.png"
    copied = SITE / "favicon.png"
    assert copied.is_file(), "thiếu `docs/site/favicon.png`"
    assert copied.read_bytes() == source.read_bytes(), (
        "favicon của trang đã lệch khỏi icon ứng dụng — chép lại "
        "`packaging/icons/nostalgia-32.png` sang `docs/site/favicon.png`"
    )
    assert 'href="favicon.png"' in HTML, "trang không còn trỏ tới `favicon.png`"
    assert "data:image/svg" not in HTML, (
        "favicon quay về SVG data-URI vẽ tay — nó không khớp icon ứng dụng"
    )


def test_the_page_still_works_when_it_is_not_served_from_the_root_of_a_domain() -> None:
    """GitHub Pages phát kho này ở `/NostalgiaLauncher/`, không ở gốc tên miền.

    Một đường dẫn bắt đầu bằng `/` (ví dụ `/style.css`) ở đó trỏ tới
    `junxmas.github.io/style.css` — ngoài kho, 404. Nguy hiểm vì nó hỏng ĐÚNG ở bản deploy
    thật và không hỏng ở đâu khác: ai mở bằng máy chủ local chạy ở gốc vẫn thấy trang hoàn
    hảo. Dùng đường dẫn tương đối hết thì cả hai nơi đều chạy.
    """
    for name, text in (("index.html", HTML), ("style.css", CSS)):
        rooted = re.findall(r'(?:src|href)="(/[^/][^"]*)"', text) + re.findall(
            r'url\(["\']?(/[^/][^"\')]*)', text
        )
        assert not rooted, f"{name}: {rooted} tuyệt đối, trỏ ra ngoài /NostalgiaLauncher/"


def test_the_link_preview_card_is_not_an_empty_box_when_someone_shares_the_page() -> None:
    """Chỗ người ta THẬT SỰ chia nhau link này là Discord, Messenger, Zalo — một người tải
    được rồi gửi cho bạn. Thiếu thẻ Open Graph thì ở đó hiện ra một ô trắng không ảnh không
    chữ, đọc ra như link rác, và đây đúng là kiểu hỏng không ai tự thấy: người dán link thấy
    thẻ hỏng, còn chủ trang thì không bao giờ nhìn vào.

    Ảnh phải ghi địa chỉ TUYỆT ĐỐI: trình quét của các nền tảng đó không chạy JavaScript và
    không giải đường dẫn tương đối, nên `og-card.jpg` trần là mất ảnh ở mọi nơi.
    """
    for prop in ("og:title", "og:description", "og:url", "og:image", "og:type"):
        assert f'property="{prop}"' in HTML, f"thiếu thẻ {prop} — thẻ xem trước sẽ trống"
    assert 'name="twitter:card" content="summary_large_image"' in HTML, (
        "thiếu twitter:card — X và vài ứng dụng chat khác sẽ hiện thẻ ảnh bé xíu"
    )

    for prop in ("og:url", "og:image"):
        found = re.search(rf'property="{prop}" content="([^"]+)"', HTML)
        assert found is not None, f"thẻ {prop} mất `content`"
        assert found.group(1).startswith(PAGES_BASE), (
            f"{prop} = {found.group(1)!r} không tuyệt đối dưới {PAGES_BASE}"
        )

    card = SITE / "og-card.jpg"
    assert card.is_file(), "thiếu `docs/site/og-card.jpg`"
    # Facebook cắt ảnh trên 8 MB; vài ứng dụng chat còn khắt khe hơn. Dư rất xa ngưỡng, nhưng
    # vượt 300 KB thì nghĩa là ai đó đã chép thẳng ảnh hero vào chứ không xuất lại.
    assert card.stat().st_size < 300_000, f"`og-card.jpg` phình lên {card.stat().st_size} byte"
    assert 'property="og:image:alt"' in HTML, (
        "ảnh thẻ không có mô tả — người dùng trình đọc màn hình gặp thẻ này trong dòng tin "
        "và chỉ nghe được 'hình ảnh'"
    )


def test_the_published_address_has_a_door_at_its_root() -> None:
    """GitHub Pages phát cả thư mục `docs/`, nên địa chỉ gốc rơi vào `docs/index.html` chứ
    không vào `docs/site/index.html`. Không có file đó thì người dán link gốc — tức là link
    ngắn nhất, link người ta sẽ nhớ và gõ lại — gặp trang 404 của GitHub.

    `.nojekyll` cũng bắt buộc: để Jekyll chạy thì nó bỏ qua mọi file bắt đầu bằng `_` khi
    dựng, và file biến mất khỏi bản deploy trong khi kho vẫn còn nó — không có cách nào
    thấy bằng mắt ở local.
    """
    docs = REPO / "docs"
    assert (docs / ".nojekyll").is_file(), "thiếu `docs/.nojekyll` — Jekyll sẽ nuốt file"

    # `entry` bị GLOSSARY §2 cấm (alias của `manifest_entry`)
    landing = docs / "index.html"
    assert landing.is_file(), "thiếu `docs/index.html` — địa chỉ gốc sẽ ra 404"
    text = landing.read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' in text and "url=site/" in text, (
        "trang gốc không chuyển hướng tới `site/`"
    )
    # Phải có liên kết bấm được, không chỉ `refresh`: tiện ích chặn `meta refresh` không
    # hiếm, và khi đó trang này là ngõ cụt.
    assert 'href="site/"' in text, "trang gốc không có liên kết thật — chặn refresh là ngõ cụt"
    # Không khai icon thì trình duyệt hỏi `/favicon.ico` ở GỐC TÊN MIỀN, ngoài kho — một 404
    # thật mỗi lượt vào. Bắt được nhờ soi bản deploy; ở local đường dẫn đó trỏ chỗ khác hẳn.
    assert 'rel="icon" type="image/png" href="site/favicon.png"' in text, (
        "trang gốc không khai icon — trình duyệt sẽ hỏi /favicon.ico ngoài kho và ăn 404"
    )


def test_the_inertia_scroll_only_takes_the_wheel_and_gives_back_every_other_route() -> None:
    """Cuộn quán tính là thứ DUY NHẤT trong trang cướp quyền của trình duyệt — nên nó cũng là
    thứ duy nhất có thể làm trang không cuộn được nữa.

    Bốn đường phải còn nguyên, và cả bốn đều hỏng im lặng vì chuột vẫn chạy nên nhìn qua
    không thấy gì:

    * `event.ctrlKey` → Ctrl+lăn là phóng to chữ của trình duyệt, một đường vào trợ năng.
      Nuốt nó là chặn người cận thị phóng trang lên.
    * `pointer: coarse` → trên điện thoại cuộn do hệ điều hành chạy ở luồng riêng, mượt sẵn
      và còn trả thanh địa chỉ đúng nhịp. Chen vào là mất cả hai.
    * `deltaMode` → Firefox báo delta theo DÒNG chứ không theo pixel. Không quy đổi thì một
      nấc lăn ở Firefox đi được 3 px, tức là trang gần như không cuộn được.
    * `passive: false` → thiếu nó thì `preventDefault()` bị bỏ qua, cuộn native chạy song
      song với vòng lặp này và trang giật hai nhịp.
    """
    assert "wheel" in JS, "mất cuộn quán tính"
    # Lọc chú thích TRƯỚC khi soi. Bản đầu của test này tìm thẳng trong `JS` và xanh cả bảng
    # trong khi ba trong năm điều kiện đã bị gỡ khỏi code — vì mỗi điều kiện đều được nhắc
    # tên trong chú thích giải thích nó, nên chuỗi vẫn còn trong file. Đã thử bằng cách gỡ
    # thật từng cái: chỉ 1/5 làm test đỏ. Chú thích là thứ KHÔNG chạy; gác theo nó là gác
    # vào lời hứa chứ không vào hành vi.
    code = strip_js_comments(JS)
    assert "const SMOOTH_WHEEL =" in code, "mất cờ bật/tắt cuộn quán tính"
    # Cắt từ ĐÚNG dòng khai cờ. Neo vào một chữ chung chung (`addEventListener`) thì đoạn cắt
    # trùm lên cả khối hiện-dần phía trên, vốn cũng dùng `STILL` — và test xanh kể cả khi
    # điều kiện ở đây đã bị gỡ. Đã thử: gỡ `!STILL` ra thì 0 test đỏ.
    inertia = code[code.index("const SMOOTH_WHEEL =") :]
    for needle, why in (
        ("!STILL", "người xin giảm chuyển động vẫn lãnh quán tính"),
        ("pointer: coarse", "cướp cả cuộn cảm ứng, vốn đã mượt sẵn ở tầng hệ điều hành"),
        ("event.ctrlKey", "nuốt cả Ctrl+lăn — mất đường phóng to chữ của trình duyệt"),
        ("deltaMode", "không quy đổi delta theo dòng — Firefox gần như không cuộn được"),
        ("passive: false", "`preventDefault()` bị bỏ qua, cuộn native chạy song song"),
    ):
        assert needle in inertia, f"{needle}: {why}"

    # Hãm theo THỜI GIAN, không theo khung hình: `remaining * 0.1` viết thẳng thì màn 120 Hz
    # hãm xong trong nửa thời gian của màn 60 Hz — cùng trang, hai cảm giác.
    #
    # Gác ở CHỖ DÙNG chứ không ở chỗ định nghĩa: tìm `Math.pow(0.9` thì một hàm `lerpOver`
    # còn nằm đó mà không ai gọi vẫn làm test xanh. Đã thử đúng vậy: đổi lời gọi về
    # `remaining * 0.1` mà bản gác cũ không đỏ.
    assert "remaining * lerpOver(dt)" in inertia, (
        "tốc độ hãm buộc vào tần số quét màn hình — phải nhân theo `dt` thật"
    )
    assert "Math.pow(0.9" in inertia, "hệ số hãm không còn là lerp 0.1 của trang mẫu"
