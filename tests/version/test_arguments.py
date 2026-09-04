"""Tham số: lọc theo luật, tách chuỗi đời cũ, và thay biến."""

from __future__ import annotations

from nostalgia.system.platform_info import Platform
from nostalgia.version.arguments import (
    resolve_argument_values,
    split_legacy_arguments,
    substitute_placeholders,
    unresolved_placeholders,
)
from nostalgia.version.meta import ArgumentSpec
from nostalgia.version.rules import Rule

LINUX = Platform(os_name="linux", os_arch="x64", os_version="6.8.0")
WINDOWS = Platform(os_name="windows", os_arch="x64", os_version="10.0.22631")


def test_rules_decide_which_arguments_survive() -> None:
    specs = (
        ArgumentSpec(values=("--luon-luon",)),
        ArgumentSpec(values=("--chi-windows",), rules=(Rule(action="allow", os_name="windows"),)),
    )
    assert resolve_argument_values(specs, LINUX) == ("--luon-luon",)
    assert resolve_argument_values(specs, WINDOWS) == ("--luon-luon", "--chi-windows")


def test_a_feature_that_is_off_removes_its_arguments() -> None:
    """Thiếu một cờ nghĩa là cờ tắt — không phải "không xét"."""
    specs = (
        ArgumentSpec(
            values=("--width", "${resolution_width}"),
            rules=(Rule(action="allow", required_features={"has_custom_resolution": True}),),
        ),
    )
    assert resolve_argument_values(specs, LINUX) == ()
    assert resolve_argument_values(specs, LINUX, {"has_custom_resolution": True}) == (
        "--width",
        "${resolution_width}",
    )


def test_nested_values_are_flattened_in_order() -> None:
    specs = (ArgumentSpec(values=("--a", "1")), ArgumentSpec(values=("--b", "2")))
    assert resolve_argument_values(specs, LINUX) == ("--a", "1", "--b", "2")


def test_the_legacy_string_splits_on_whitespace() -> None:
    assert split_legacy_arguments("--username ${auth_player_name}  --demo") == (
        "--username",
        "${auth_player_name}",
        "--demo",
    )
    assert split_legacy_arguments("") == ()


def test_a_value_with_spaces_does_not_split_because_it_is_filled_in_later() -> None:
    """Tách TRƯỚC rồi mới điền giá trị, nên tên người chơi có khoảng trắng vẫn là một tham số."""
    tokens = split_legacy_arguments("--username ${auth_player_name}")
    filled = substitute_placeholders(tokens, {"auth_player_name": "Hai Tu"})
    assert filled == ("--username", "Hai Tu")


def test_substitution_handles_several_variables_inside_one_token() -> None:
    values = ("-Dchỗ=${a}/${b}", "${a}")
    assert substitute_placeholders(values, {"a": "1", "b": "2"}) == ("-Dchỗ=1/2", "1")


def test_an_unknown_variable_is_left_alone_not_blanked() -> None:
    """Thay bằng rỗng sẽ đẩy một tham số câm vào lệnh và game hỏng ở chỗ chẳng liên quan."""
    assert substitute_placeholders(("${la_hoac}",), {"khac": "x"}) == ("${la_hoac}",)


def test_camel_case_variables_are_recognised() -> None:
    """Mojang dùng cả `auth_player_name` lẫn `quickPlayPath` trong cùng một file."""
    assert substitute_placeholders(("${quickPlayPath}",), {"quickPlayPath": "p"}) == ("p",)


def test_leftover_variables_can_be_listed() -> None:
    assert unresolved_placeholders(("ok", "${a}", "x${b}y")) == ("${a}", "${b}")
    assert unresolved_placeholders(("ok",)) == ()


def test_a_dollar_sign_without_braces_is_not_a_variable() -> None:
    assert substitute_placeholders(("giá $5", "$notavar"), {"notavar": "x"}) == (
        "giá $5",
        "$notavar",
    )
