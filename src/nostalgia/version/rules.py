"""Luật `rules` của Mojang: quyết định một thư viện hay một tham số có được dùng không.

Thuật toán đúng, và dễ làm sai: **không có luật nào thì cho phép**; có luật thì mặc định
từ chối, rồi mỗi luật KHỚP với môi trường sẽ ghi đè kết quả — luật sau thắng luật trước.

Ví dụ thật của 1.8.9: `[{allow}, {disallow, os: osx}]`. Trên Linux, luật đầu khớp (không
điều kiện) nên cho phép, luật sau không khớp nên giữ nguyên. Trên macOS, luật sau khớp nên
đổi thành từ chối. Nếu cài đặt sai thứ tự ghi đè, thư viện này sẽ bị nạp trên macOS và game
sẽ chết vì xung đột LWJGL.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from nostalgia.model.json_value import JsonValue, as_mapping, as_string
from nostalgia.system.platform_info import Platform

ALLOW = "allow"
DISALLOW = "disallow"


@dataclass(frozen=True, slots=True)
class Rule:
    """Một luật đã phân tích. Trường `None` nghĩa là "không xét điều kiện này"."""

    action: str
    os_name: str | None = None
    os_arch: str | None = None
    os_version_pattern: str | None = None
    required_features: Mapping[str, bool] = field(default_factory=dict)

    def matches(self, platform: Platform, features: Mapping[str, bool]) -> bool:
        """Luật có áp vào môi trường này không. Mọi điều kiện đã khai đều phải đúng."""
        if self.os_name is not None and self.os_name != platform.os_name:
            return False
        if self.os_arch is not None and self.os_arch != platform.os_arch:
            return False
        if self.os_version_pattern is not None and not re.search(
            self.os_version_pattern, platform.os_version
        ):
            return False
        return all(
            features.get(name, False) == expected
            for name, expected in self.required_features.items()
        )


def parse_rules(raw_rules: JsonValue) -> tuple[Rule, ...]:
    """Phân tích danh sách luật thô. Khoá lạ bị bỏ qua để Mojang thêm khoá mới không làm nổ."""
    if not isinstance(raw_rules, list):
        return ()
    return tuple(_parse_rule(raw) for raw in raw_rules if isinstance(raw, dict))


def rules_allow(
    rules: tuple[Rule, ...],
    platform: Platform,
    features: Mapping[str, bool] | None = None,
) -> bool:
    """Với môi trường này, tập luật cho phép hay không.

    `features` là các cờ tính năng của Mojang (`is_demo_user`, `has_custom_resolution`,
    `has_quick_plays_support`...). Thiếu một cờ nghĩa là cờ đó tắt.
    """
    if not rules:
        return True
    active_features = features or {}
    allowed = False
    for rule in rules:
        if rule.matches(platform, active_features):
            allowed = rule.action == ALLOW
    return allowed


def _parse_rule(rule_fields: dict[str, JsonValue]) -> Rule:
    operating_system = as_mapping(rule_fields.get("os"))
    features = {
        name: bool(value) for name, value in as_mapping(rule_fields.get("features")).items()
    }
    return Rule(
        action=as_string(rule_fields.get("action")) or DISALLOW,
        os_name=as_string(operating_system.get("name")),
        os_arch=as_string(operating_system.get("arch")),
        os_version_pattern=as_string(operating_system.get("version")),
        required_features=features,
    )
