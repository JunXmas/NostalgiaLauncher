"""Kiểu cho dữ liệu JSON chưa tin được.

JSON đọc từ đĩa hay từ mạng là dữ liệu **không tin được**, nên kiểu của nó phải nói đúng
điều đó. Dùng `Any` sẽ khiến bộ kiểm kiểu im lặng ở mọi chỗ dùng về sau; kiểu đệ quy này
buộc người gọi thu hẹp kiểu trước khi dùng.

Đặt ở `model/` chứ không ở `storage/files.py`: cả tầng đọc file và tầng phân tích phiên bản
đều cần nó, mà `version/` phải thuần nên không được phụ thuộc vào module đọc/ghi file.
"""

from __future__ import annotations

type JsonValue = bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"] | None


def as_mapping(value: JsonValue) -> dict[str, JsonValue]:
    """Trả về `value` nếu nó là đối tượng JSON, ngược lại trả về đối tượng rỗng.

    Có mặt vì mẫu `x = d.get("k"); if not isinstance(x, dict): x = {}` lặp lại ở mọi chỗ
    phân tích JSON, và viết tay mỗi lần là chỗ để lọt lỗi.
    """
    return value if isinstance(value, dict) else {}


def as_list(value: JsonValue) -> list[JsonValue]:
    """Trả về `value` nếu nó là mảng JSON, ngược lại trả về mảng rỗng."""
    return value if isinstance(value, list) else []


def as_string(value: JsonValue) -> str | None:
    """Trả về `value` nếu nó là chuỗi, ngược lại `None`. Không ép kiểu số thành chuỗi."""
    return value if isinstance(value, str) else None


def as_integer(value: JsonValue) -> int | None:
    """Trả về `value` nếu nó là số nguyên. `bool` bị loại vì trong Python nó là con của int."""
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None
