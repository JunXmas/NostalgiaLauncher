"""Đọc TỐI THIỂU file NBT nén gzip của Minecraft (`level.dat`): chỉ lấy tên thế giới và mốc
chơi cuối trong compound `Data`, bỏ qua mọi thứ khác.

Không có thư viện NBT nào trong kho và cũng không cần: hai trường string/long là đủ cho ô
CHƠI TIẾP. Bộ đọc có trần kích thước và độ sâu, mọi độ dài đều được so với phần payload còn
lại trước khi cắt, và file hỏng kiểu gì cũng trả `None` chứ không ném — một `level.dat` lạ
không được làm hỏng trang chủ.
"""

from __future__ import annotations

import gzip
import struct
from dataclasses import dataclass
from pathlib import Path

# level.dat thật cỡ 10-200 KB; trần rộng để không bao giờ chạm với file lành.
MAX_LEVEL_BYTES = 8 * 1024 * 1024
MAX_DEPTH = 32

TAG_END, TAG_BYTE, TAG_SHORT, TAG_INT, TAG_LONG = 0, 1, 2, 3, 4
TAG_FLOAT, TAG_DOUBLE, TAG_BYTE_ARRAY, TAG_STRING = 5, 6, 7, 8
TAG_LIST, TAG_COMPOUND, TAG_INT_ARRAY, TAG_LONG_ARRAY = 9, 10, 11, 12
SCALAR_SIZES = {TAG_BYTE: 1, TAG_SHORT: 2, TAG_INT: 4, TAG_LONG: 8, TAG_FLOAT: 4, TAG_DOUBLE: 8}
ARRAY_ELEMENT_SIZES = {TAG_BYTE_ARRAY: 1, TAG_INT_ARRAY: 4, TAG_LONG_ARRAY: 8}
DATA_COMPOUND_NAME = "Data"
WORLD_NAME_TAG = "LevelName"
LAST_PLAYED_TAG = "LastPlayed"
READ_ERRORS = (OSError, EOFError, struct.error, IndexError, UnicodeDecodeError, ValueError)


@dataclass(frozen=True, slots=True)
class LevelSummary:
    """Hai trường trang chủ cần. `last_played_ms` là mili giây epoch, 0 nếu file không ghi."""

    world_name: str
    last_played_ms: int


class Reader:
    """Con trỏ đọc big-endian trên payload đã giải nén."""

    __slots__ = ("offset", "payload")

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.offset = 0

    def unpack(self, layout: str) -> int:
        (value,) = struct.unpack_from(">" + layout, self.payload, self.offset)
        self.offset += struct.calcsize(layout)
        return int(value)

    def skip(self, count: int) -> None:
        if count < 0 or count > len(self.payload) - self.offset:
            message = "độ dài NBT vượt phần payload còn lại"
            raise ValueError(message)
        self.offset += count

    def take(self, count: int) -> bytes:
        start = self.offset
        self.skip(count)
        return self.payload[start : self.offset]

    def text(self) -> str:
        return self.take(self.unpack("H")).decode("utf-8", errors="replace")

    def remaining(self) -> int:
        return len(self.payload) - self.offset


def skip_payload(reader: Reader, tag_id: int, depth: int) -> None:
    """Nhảy qua payload của một tag mà không giữ gì. Đệ quy có trần độ sâu."""
    if depth > MAX_DEPTH:
        message = "NBT lồng quá sâu"
        raise ValueError(message)
    if tag_id in SCALAR_SIZES:
        reader.skip(SCALAR_SIZES[tag_id])
    elif tag_id in ARRAY_ELEMENT_SIZES:
        reader.skip(reader.unpack("i") * ARRAY_ELEMENT_SIZES[tag_id])
    elif tag_id == TAG_STRING:
        reader.skip(reader.unpack("H"))
    elif tag_id == TAG_LIST:
        element_tag = reader.unpack("B")
        count = reader.unpack("i")
        # Mỗi phần tử chiếm ít nhất một byte: số phần tử lớn hơn phần còn lại là file hỏng.
        if count > reader.remaining():
            message = "danh sách NBT khai nhiều phần tử hơn dữ liệu"
            raise ValueError(message)
        for _ in range(count):
            skip_payload(reader, element_tag, depth + 1)
    elif tag_id == TAG_COMPOUND:
        while True:
            child_tag = reader.unpack("B")
            if child_tag == TAG_END:
                return
            reader.skip(reader.unpack("H"))
            skip_payload(reader, child_tag, depth + 1)
    else:
        message = f"tag NBT lạ {tag_id}"
        raise ValueError(message)


def _read_fields(reader: Reader, depth: int) -> dict[str, int | str]:
    """Đọc các con string / int / long của một compound; chui vào đúng compound `Data` ở gốc,
    còn lại nhảy qua."""
    if depth > MAX_DEPTH:
        message = "NBT lồng quá sâu"
        raise ValueError(message)
    fields: dict[str, int | str] = {}
    while True:
        child_tag = reader.unpack("B")
        if child_tag == TAG_END:
            return fields
        name = reader.text()
        if child_tag == TAG_STRING:
            fields[name] = reader.text()
        elif child_tag == TAG_INT:
            fields[name] = reader.unpack("i")
        elif child_tag == TAG_LONG:
            fields[name] = reader.unpack("q")
        elif child_tag == TAG_COMPOUND and depth == 0 and name == DATA_COMPOUND_NAME:
            fields.update(_read_fields(reader, depth + 1))
        else:
            skip_payload(reader, child_tag, depth + 1)


def load_level_summary(level_path: Path) -> LevelSummary | None:
    """Tên và mốc chơi cuối của một thế giới; `None` nếu file thiếu, hỏng, quá to hay quá sâu."""
    try:
        with gzip.open(level_path, "rb") as stream:
            payload = stream.read(MAX_LEVEL_BYTES + 1)
        if len(payload) > MAX_LEVEL_BYTES:
            return None
        reader = Reader(payload)
        if reader.unpack("B") != TAG_COMPOUND:
            return None
        reader.text()  # tên compound gốc, thường rỗng
        fields = _read_fields(reader, 0)
    except READ_ERRORS:
        return None
    world_name = fields.get(WORLD_NAME_TAG)
    last_played = fields.get(LAST_PLAYED_TAG)
    return LevelSummary(
        world_name=world_name if isinstance(world_name, str) else "",
        last_played_ms=last_played if isinstance(last_played, int) else 0,
    )
