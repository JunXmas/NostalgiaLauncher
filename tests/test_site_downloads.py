"""Con số lượt tải trên trang, qua lần kho được dựng lại dưới PolyForm Strict.

Tách khỏi `test_site.py` vì file đó đã chạm trần 200 dòng code của kho — và luật đó áp cho
cả file test. Gộp vào thì phải nới trần, tức là đổi một luật chung để chứa một test riêng.
"""

from __future__ import annotations

import re

from site_sources import HTML, JS, strip_js_comments


def test_the_download_count_survives_the_move_to_the_relicensed_repo() -> None:
    """Kho được dựng lại dưới PolyForm Strict, và GitHub đặt `download_count` về 0 cho mọi
    asset vừa tải lên — lượt tải KHÔNG chuyển kho được. API của kho mới chỉ trả về lượt tải
    phát sinh SAU khi chuyển.

    Cái hỏng mà không ai thấy: hàm đếm cộng từ 0 nên nó trả về một con số DƯƠNG và nhỏ (vài
    lượt), `total <= 0` không chặn được, số tĩnh trong HTML bị ghi đè. Đo bằng trình duyệt
    thật trên API giả của kho mới: 776 khi có mốc, 18 khi không. Lối dự phòng của con số tĩnh
    chỉ gác được trường hợp API IM, không gác được trường hợp API trả lời ĐÚNG nhưng thiếu.

    Gác ở MÃ ĐÃ LỌC CHÚ THÍCH, cùng lý do như các test gác `app.js` khác: tên hằng số có mặt
    trong chính chú thích giải thích nó, nên soi nguyên file thì gỡ vá ra test vẫn xanh.
    """
    code = strip_js_comments(JS)
    counter = re.search(r"function countDownloads\(.*?\n\}", code, re.S)
    assert counter is not None, "mất hàm `countDownloads`"
    assert "DOWNLOADS_BEFORE_RELICENSE" in counter.group(0), (
        "hàm đếm không cộng mốc lượt tải trước lúc đổi giấy phép — lượt tải của kho cũ không "
        "chuyển sang được, trang sẽ khoe một con số nhỏ hơn sự thật rất nhiều"
    )


def test_the_static_count_is_not_lower_than_the_baseline() -> None:
    """Số viết sẵn trong HTML là thứ người không chạy JavaScript đọc. Thấp hơn mốc thì hai
    nhóm người dùng đọc ra hai con số khác nhau, và nhóm không-JS đọc ra con số thấp hơn —
    đúng chiều hỏng mà cả test trên đang cố chặn, chỉ khác lối vào.
    """
    declared = re.search(r"const DOWNLOADS_BEFORE_RELICENSE = (\d+);", strip_js_comments(JS))
    assert declared is not None, "mất khai báo `DOWNLOADS_BEFORE_RELICENSE`"
    found = re.search(r'id="download-total"[^>]*>([^<]*)<', HTML)
    assert found is not None, "mất ô lượt tải"
    static, baseline = int(re.sub(r"\D", "", found.group(1)) or 0), int(declared.group(1))
    assert static >= baseline, (
        f"ô tĩnh ghi {static} mà mốc trước lúc đổi giấy phép đã là {baseline} — người không "
        f"chạy JavaScript đọc ra con số thấp hơn sự thật"
    )
