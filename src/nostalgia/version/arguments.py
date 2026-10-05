"""Tham số khởi động: lọc theo luật, trải phẳng, và thay biến. THUẦN: không I/O.

Ở đây gói trọn khác biệt giữa hai đời định dạng:

- **≤1.12**: `minecraftArguments` là MỘT CHUỖI, tách theo khoảng trắng, không có luật nào.
- **≥1.13**: `arguments.game` và `arguments.jvm` là DANH SÁCH, phần tử có thể là chuỗi trần
  hoặc `{rules, value}` với `value` là chuỗi hay danh sách.

Luật thay biến quan trọng nhất: **biến không biết thì GIỮ NGUYÊN**, không thay bằng chuỗi
rỗng. Bản mod hay bản mới của Mojang có thể dùng biến ta chưa biết; thay bằng rỗng sẽ đẩy
một tham số câm vào lệnh và game hỏng ở chỗ chẳng liên quan gì. Giữ nguyên thì test
"không còn `${` nào trong lệnh" phát hiện ra ngay.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from nostalgia.system.platform_info import Platform
from nostalgia.version.meta import ArgumentSpec
from nostalgia.version.rules import rules_allow

# Tên biến của Mojang có cả `snake_case` (`auth_player_name`) lẫn `camelCase`
# (`quickPlayPath`) — bắt cả hai.
PLACEHOLDER_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def resolve_argument_values(
    specs: tuple[ArgumentSpec, ...],
    platform: Platform,
    features: Mapping[str, bool] | None = None,
) -> tuple[str, ...]:
    """Bỏ những tham số mà luật không cho phép, rồi trải danh sách lồng thành một chuỗi phẳng."""
    values: list[str] = []
    for spec in specs:
        if rules_allow(spec.rules, platform, features):
            values.extend(spec.values)
    return tuple(values)


def split_legacy_arguments(minecraft_arguments: str) -> tuple[str, ...]:
    """Tách chuỗi tham số đời cũ.

    Tách theo khoảng trắng là đúng: Mojang không bao giờ đặt dấu nháy hay khoảng trắng bên
    trong một tham số ở khoá này, và giá trị thật được điền vào SAU khi tách, nên tên người
    chơi có khoảng trắng cũng không tách nhầm thành hai tham số.
    """
    return tuple(minecraft_arguments.split())


def substitute_placeholders(
    values: tuple[str, ...], variables: Mapping[str, str]
) -> tuple[str, ...]:
    """Thay `${tên}` bằng giá trị. Biến không biết thì giữ nguyên nguyên văn."""

    def replace(match: re.Match[str]) -> str:
        return variables.get(match.group(1), match.group(0))

    return tuple(PLACEHOLDER_PATTERN.sub(replace, value) for value in values)


def unresolved_placeholders(values: tuple[str, ...]) -> tuple[str, ...]:
    """Những biến còn sót lại sau khi thay — dùng để chặn lệnh hỏng trước khi chạy."""
    return tuple(
        match.group(0) for value in values for match in PLACEHOLDER_PATTERN.finditer(value)
    )
