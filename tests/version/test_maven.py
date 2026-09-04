"""Toạ độ maven: đường dẫn trong kho `libraries/` suy ra từ đây, và chỉ từ đây."""

from __future__ import annotations

import pytest

from mccore.version.maven import MavenCoordinate


def test_parses_three_parts() -> None:
    coordinate = MavenCoordinate.parse("com.google.guava:guava:32.1.2-jre")
    assert (coordinate.group, coordinate.artifact, coordinate.artifact_version) == (
        "com.google.guava",
        "guava",
        "32.1.2-jre",
    )
    assert coordinate.classifier is None


def test_parses_a_classifier() -> None:
    """Natives kiểu mới nằm ở phần thứ tư của toạ độ."""
    coordinate = MavenCoordinate.parse("org.lwjgl:lwjgl-glfw:3.3.1:natives-linux")
    assert coordinate.classifier == "natives-linux"


def test_relative_path_uses_forward_slashes_everywhere() -> None:
    """Chuỗi này đi vào URL và vào khoá JSON, nên luôn `/` kể cả trên Windows."""
    coordinate = MavenCoordinate.parse("org.lwjgl:lwjgl-glfw:3.3.1:natives-linux")
    assert coordinate.relative_path == (
        "org/lwjgl/lwjgl-glfw/3.3.1/lwjgl-glfw-3.3.1-natives-linux.jar"
    )


def test_relative_path_without_classifier() -> None:
    coordinate = MavenCoordinate.parse("com.google.guava:guava:32.1.2-jre")
    assert coordinate.relative_path == "com/google/guava/guava/32.1.2-jre/guava-32.1.2-jre.jar"


def test_dedupe_key_ignores_the_version() -> None:
    """Fabric mang `asm 9.10.1`, vanilla khai `asm 9.6`; để cả hai lên classpath là lỗi
    "duplicate classes found" mà launcher tiền nhiệm từng gặp."""
    loader_asm = MavenCoordinate.parse("org.ow2.asm:asm:9.10.1")
    vanilla_asm = MavenCoordinate.parse("org.ow2.asm:asm:9.6")
    assert loader_asm.dedupe_key == vanilla_asm.dedupe_key


def test_dedupe_key_keeps_the_classifier_apart() -> None:
    """Cùng thư viện nhưng natives của hai hệ điều hành là hai thứ khác nhau."""
    linux = MavenCoordinate.parse("org.lwjgl:lwjgl:3.3.1:natives-linux")
    windows = MavenCoordinate.parse("org.lwjgl:lwjgl:3.3.1:natives-windows")
    plain = MavenCoordinate.parse("org.lwjgl:lwjgl:3.3.1")
    assert linux.dedupe_key != windows.dedupe_key
    assert linux.dedupe_key != plain.dedupe_key


@pytest.mark.parametrize("name", ["", "chi-mot-phan", "hai:phan"])
def test_too_few_parts_is_an_error(name: str) -> None:
    with pytest.raises(ValueError, match="group:artifact:version"):
        MavenCoordinate.parse(name)


def test_empty_classifier_is_treated_as_absent() -> None:
    assert MavenCoordinate.parse("a:b:c:").classifier is None


def test_string_form_round_trips() -> None:
    for name in ("a.b:c:1.0", "a.b:c:1.0:natives-linux"):
        assert str(MavenCoordinate.parse(name)) == name
