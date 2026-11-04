"""Jar phải đúng mod, đúng game và không bị hỏng dù phần mở rộng vẫn là .jar."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from nos_fixture import build_nos_jar
from nostalgia.nos_client.artifact import verify_mod_artifact


def test_valid_zip_and_hash(tmp_path: Path) -> None:
    path = tmp_path / "client.jar"
    body = build_nos_jar()
    path.write_bytes(body)
    assert verify_mod_artifact(
        path, "1.21.11", sha256=hashlib.sha256(body).hexdigest(), size=len(body)
    )
    assert not verify_mod_artifact(path, "26.2")
    assert not verify_mod_artifact(path, "1.21.11", sha256="0" * 64)
    assert not verify_mod_artifact(path, "1.21.11", size=len(body) + 1)


@pytest.mark.parametrize("body", [b"PK fake jar", build_nos_jar(mod_id="other"), b""])
def test_invalid_mod_is_rejected(tmp_path: Path, body: bytes) -> None:
    path = tmp_path / "client.jar"
    path.write_bytes(body)
    assert not verify_mod_artifact(path, "1.21.11")


def test_missing_jar_is_rejected(tmp_path: Path) -> None:
    assert not verify_mod_artifact(tmp_path / "missing.jar", "1.21.11")


@pytest.mark.parametrize(
    ("loader_requirement", "java_requirement"),
    [
        (">=0.20.0", ">=21"),
        (">=0.19.3", ">=25"),
    ],
)
def test_newer_runtime_requirements_do_not_replace_working_client(
    tmp_path: Path,
    loader_requirement: str,
    java_requirement: str,
) -> None:
    path = tmp_path / "client.jar"
    path.write_bytes(
        build_nos_jar(loader_version=loader_requirement, java_requirement=java_requirement)
    )
    assert not verify_mod_artifact(path, "1.21.11", loader_version="0.19.3")


def test_mislabeled_version_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "client.jar"
    path.write_bytes(build_nos_jar())
    assert not verify_mod_artifact(path, "1.21.11", mod_version="0.4.3")
