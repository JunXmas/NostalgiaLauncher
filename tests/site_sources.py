"""Đọc ba file của trang tải, và cắt chú thích khỏi JavaScript trước khi soi.

Tách khỏi `test_site.py` vì đây là hạ tầng, không phải phép kiểm: `strip_js_comments` là
~45 dòng đi-theo-ký-tự, nằm chung thì nó chiếm một phần tư ngân sách 200 dòng của file test
và mỗi lần thêm một phép kiểm lại phải nén lời giải thích của phép kiểm khác.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "docs" / "site"
# Địa chỉ công khai, suy ra từ chủ kho và tên kho. Ghim ở một chỗ vì nó xuất hiện trong
# `canonical`, `og:url`, `og:image` — lệch một cái là thẻ xem trước trỏ vào hư vô.
PAGES_BASE = "https://junxmas.github.io/NostalgiaLauncher/site/"

HTML = (SITE / "index.html").read_text(encoding="utf-8")
JS = (SITE / "app.js").read_text(encoding="utf-8")
CSS = (SITE / "style.css").read_text(encoding="utf-8")


def strip_js_comments(source: str) -> str:
    """Bỏ `//…` và `/*…*/`, giữ nguyên nội dung chuỗi.

    Cần vì `app.js` chú thích rất dày và chú thích luôn nhắc tên đúng thứ nó giải thích —
    nên mọi test tìm-chuỗi chạy trên nguyên file sẽ xanh kể cả khi code đã bị gỡ.

    Không dùng regex: `"https://x"` có `//` ở giữa một chuỗi, regex ngây thơ sẽ cắt mất nửa
    dòng và test đỏ oan. Phải đi qua từng ký tự với trạng thái "đang trong chuỗi hay không".
    """
    out = []
    i = 0
    quote = None
    while i < len(source):
        ch = source[i]
        if quote:
            out.append(ch)
            if ch == "\\":
                if i + 1 < len(source):
                    out.append(source[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
        elif ch in "\"'`":
            quote = ch
            out.append(ch)
            i += 1
        elif source.startswith("//", i):
            i = source.find("\n", i)
            if i == -1:
                break
        elif source.startswith("/*", i):
            end = source.find("*/", i + 2)
            i = len(source) if end == -1 else end + 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)
