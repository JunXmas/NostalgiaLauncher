"""Server đã thêm trong game (`servers.dat` của một bản chơi) — tab Multiplayer khi bấm Chơi.

`servers.dat` là NBT KHÔNG nén: compound gốc → list `servers` gồm các compound `{name, ip,
icon (PNG base64), hidden}`. Chỉ đọc đĩa, có trần kích thước, file hỏng → rỗng. Icon được kiểm
(base64 hợp lệ, đúng chữ ký PNG, ≤ 32 KiB) rồi đưa cho QML dạng URL `data:` — không ghi cache,
không chạm mạng, không ping.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

from nostalgia.instance.nbt import (
    READ_ERRORS,
    TAG_BYTE,
    TAG_COMPOUND,
    TAG_END,
    TAG_LIST,
    TAG_STRING,
    Reader,
    skip_payload,
)

SERVERS_FILE_NAME = "servers.dat"
MAX_SERVERS_BYTES = 1024 * 1024
# Icon server là PNG 64x64 (vài KB); chuỗi NBT tối đa 65535 byte nên base64 không thể to hơn.
MAX_ICON_BYTES = 32 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SERVERS_LIST_TAG = "servers"


@dataclass(frozen=True, slots=True)
class SavedServer:
    """Một dòng trong servers.dat. `icon_base64` rỗng nếu game chưa lấy được icon hoặc icon hỏng."""

    server_name: str
    address: str
    icon_base64: str

    @property
    def icon_url(self) -> str:
        """URL `data:` cho `Image` của QML, rỗng khi không có icon."""
        return f"data:image/png;base64,{self.icon_base64}" if self.icon_base64 else ""


def checked_icon(icon_base64: str) -> str:
    """Chỉ giữ icon là PNG thật, cỡ vừa phải; còn lại coi như không có."""
    try:
        decoded = base64.b64decode(icon_base64, validate=True)
    except ValueError:  # binascii.Error là ValueError
        return ""
    if not decoded.startswith(PNG_SIGNATURE) or len(decoded) > MAX_ICON_BYTES:
        return ""
    return icon_base64


def _read_server(reader: Reader) -> SavedServer | None:
    """Một compound server: giữ name / ip / icon, cờ hidden; tag khác nhảy qua."""
    fields: dict[str, str] = {}
    hidden = False
    while True:
        child_tag = reader.unpack("B")
        if child_tag == TAG_END:
            break
        name = reader.text()
        if child_tag == TAG_STRING:
            fields[name] = reader.text()
        elif child_tag == TAG_BYTE:
            # Luôn tiêu thụ byte (kể cả acceptTextures) rồi mới xét — không được short-circuit.
            flag = reader.unpack("b")
            hidden = hidden or (name == "hidden" and flag == 1)
        else:
            skip_payload(reader, child_tag, 1)
    address = fields.get("ip", "").strip()
    if hidden or not address:
        return None
    return SavedServer(
        server_name=fields.get("name", "").strip() or address,
        address=address,
        icon_base64=checked_icon(fields.get("icon", "")),
    )


def load_saved_servers(servers_path: Path) -> tuple[SavedServer, ...]:
    """Danh sách server theo đúng thứ tự trong game; file thiếu / hỏng / quá to → rỗng."""
    try:
        if servers_path.stat().st_size > MAX_SERVERS_BYTES:
            return ()
        reader = Reader(servers_path.read_bytes())
        if reader.unpack("B") != TAG_COMPOUND:
            return ()
        reader.text()  # tên compound gốc, rỗng
        servers: list[SavedServer] = []
        while True:
            child_tag = reader.unpack("B")
            if child_tag == TAG_END:
                return tuple(servers)
            name = reader.text()
            if child_tag != TAG_LIST or name != SERVERS_LIST_TAG:
                skip_payload(reader, child_tag, 1)
                continue
            element_tag = reader.unpack("B")
            count = reader.unpack("i")
            if count <= 0:
                continue
            if element_tag != TAG_COMPOUND or count > reader.remaining():
                return ()
            for _ in range(count):
                saved = _read_server(reader)
                if saved is not None:
                    servers.append(saved)
    except READ_ERRORS:
        return ()
