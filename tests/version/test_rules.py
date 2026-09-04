"""Luật `rules`: chỗ dễ sai nhất của định dạng, và kiểm được 100% offline.

Nền tảng là đối số của hàm, nên kiểm được hành vi trên Windows và macOS ngay khi đang ngồi
trên Linux — không cần máy ảo, không cần CI đa nền tảng.
"""

from __future__ import annotations

import pytest

from nostalgia.system.platform_info import Platform
from nostalgia.version.rules import Rule, parse_rules, rules_allow

LINUX = Platform(os_name="linux", os_arch="x64", os_version="6.8.0-generic")
MACOS = Platform(os_name="osx", os_arch="arm64", os_version="23.5.0")
WINDOWS = Platform(os_name="windows", os_arch="x64", os_version="10.0.22631")
WINDOWS_32 = Platform(os_name="windows", os_arch="x86", os_version="10.0.19045")


def test_no_rules_means_allowed() -> None:
    assert rules_allow((), LINUX) is True


def test_rules_present_but_none_matching_means_denied() -> None:
    """Có luật mà không luật nào khớp thì TỪ CHỐI. Mặc định cho phép là lỗi kinh điển."""
    rules = parse_rules([{"action": "allow", "os": {"name": "osx"}}])
    assert rules_allow(rules, LINUX) is False
    assert rules_allow(rules, MACOS) is True


def test_a_later_rule_overrides_an_earlier_one() -> None:
    """Mẫu thật của 1.8.9: cho phép mọi nơi, RỒI từ chối riêng macOS.

    Nếu cài đặt sai thứ tự ghi đè, thư viện LWJGL này sẽ bị nạp trên macOS và game chết.
    """
    rules = parse_rules([{"action": "allow"}, {"action": "disallow", "os": {"name": "osx"}}])
    assert rules_allow(rules, LINUX) is True
    assert rules_allow(rules, WINDOWS) is True
    assert rules_allow(rules, MACOS) is False


def test_architecture_is_matched() -> None:
    rules = parse_rules([{"action": "allow", "os": {"name": "windows", "arch": "x86"}}])
    assert rules_allow(rules, WINDOWS_32) is True
    assert rules_allow(rules, WINDOWS) is False


def test_os_version_is_a_regular_expression() -> None:
    rules = parse_rules([{"action": "allow", "os": {"name": "osx", "version": r"^10\.5\."}}])
    assert rules_allow(rules, Platform("osx", "x64", "10.5.8")) is True
    assert rules_allow(rules, Platform("osx", "x64", "10.15.7")) is False


def test_features_must_match_exactly() -> None:
    """Mẫu thật của 1.20.1: tham số `--demo` chỉ áp khi bật cờ `is_demo_user`."""
    rules = parse_rules([{"action": "allow", "features": {"is_demo_user": True}}])
    assert rules_allow(rules, LINUX, {"is_demo_user": True}) is True
    assert rules_allow(rules, LINUX, {"is_demo_user": False}) is False
    assert rules_allow(rules, LINUX) is False, "thiếu cờ nghĩa là cờ tắt"


def test_a_rule_requiring_a_feature_to_be_off() -> None:
    rules = parse_rules([{"action": "allow", "features": {"has_custom_resolution": False}}])
    assert rules_allow(rules, LINUX) is True
    assert rules_allow(rules, LINUX, {"has_custom_resolution": True}) is False


def test_all_conditions_of_one_rule_must_hold() -> None:
    rules = parse_rules(
        [
            {
                "action": "allow",
                "os": {"name": "linux", "arch": "x64"},
                "features": {"is_demo_user": True},
            }
        ]
    )
    assert rules_allow(rules, LINUX, {"is_demo_user": True}) is True
    assert rules_allow(rules, LINUX) is False
    assert rules_allow(rules, WINDOWS, {"is_demo_user": True}) is False


@pytest.mark.parametrize("garbage", [None, "khong phai danh sach", 42, {"action": "allow"}])
def test_malformed_rules_are_ignored_not_fatal(garbage: object) -> None:
    """Mojang thêm khoá mới liên tục; dữ liệu lạ không được làm launcher nổ."""
    assert parse_rules(garbage) == ()  # type: ignore[arg-type]


def test_unknown_keys_inside_a_rule_are_ignored() -> None:
    rules = parse_rules([{"action": "allow", "khoa_moi_cua_mojang": {"gi_do": 1}}])
    assert rules_allow(rules, LINUX) is True


def test_missing_action_is_treated_as_disallow() -> None:
    """Thiếu `action` thì chọn phía an toàn: không dùng thư viện đó."""
    assert rules_allow(parse_rules([{"os": {"name": "linux"}}]), LINUX) is False


def test_rule_is_frozen() -> None:
    rule = Rule(action="allow")
    with pytest.raises(AttributeError):
        rule.action = "disallow"  # type: ignore[misc]
