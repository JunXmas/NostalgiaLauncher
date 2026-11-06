"""Kiểm chữ ký và biên giải nén trước khi chạy mã của bản phát hành."""

import base64
import io
import stat
import tarfile
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from nostalgia.errors import IntegrityError, UnsafePathError
from nostalgia.horizon.archive import extract_horizon_bundle
from nostalgia.horizon.release import verify_release_signature
from nostalgia.operations.cancellation import CancelToken


def test_signature_pins_checksums_and_release_context(monkeypatch: pytest.MonkeyPatch) -> None:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    monkeypatch.setattr(
        "nostalgia.horizon.release.RELEASE_KEY", base64.b64encode(public_key).decode()
    )
    checksums = b"a" * 64 + b"  horizon-linux-x86_64.tar.gz\n"
    signature = base64.b64encode(private_key.sign(b"horizon release nightly\n" + checksums))
    verify_release_signature(checksums, signature)
    with pytest.raises(IntegrityError):
        verify_release_signature(checksums + b"changed", signature)
    wrong_tag = base64.b64encode(private_key.sign(b"horizon release other\n" + checksums))
    with pytest.raises(IntegrityError):
        verify_release_signature(checksums, wrong_tag)
    with pytest.raises(IntegrityError):
        verify_release_signature(checksums, b"invalid base64!")


def test_zip_preserves_whole_build_and_executable_permissions(tmp_path: Path) -> None:
    archive_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        executable = zipfile.ZipInfo("horizon/horizon-client")
        executable.external_attr = (stat.S_IFREG | 0o755) << 16
        archive.writestr(executable, b"native binary")
        archive.writestr("horizon/research-lock.json", "{}")
        archive.writestr("horizon/exporters/manifest.json", "{}")
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    build_dir = extract_horizon_bundle(archive_path, staging_dir)
    assert (build_dir / "horizon-client").read_bytes() == b"native binary"
    assert (build_dir / "horizon-client").stat().st_mode & 0o111
    assert (build_dir / "exporters/manifest.json").is_file()


@pytest.mark.parametrize("path_text", ["../escape", "/escape", "C:/escape", "horizon/../../escape"])
def test_zip_rejects_path_escape(tmp_path: Path, path_text: str) -> None:
    archive_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(path_text, b"forbidden")
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    with pytest.raises((IntegrityError, UnsafePathError)):
        extract_horizon_bundle(archive_path, staging_dir)
    assert not (tmp_path / "escape").exists()


@pytest.mark.parametrize("file_kind", [stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR, stat.S_IFSOCK])
def test_zip_rejects_links_and_special_files(tmp_path: Path, file_kind: int) -> None:
    archive_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        member = zipfile.ZipInfo("horizon/unsafe")
        member.external_attr = (file_kind | 0o755) << 16
        archive.writestr(member, b"forbidden")
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    with pytest.raises(IntegrityError, match="link or special file"):
        extract_horizon_bundle(archive_path, staging_dir)
    assert not list(staging_dir.iterdir())


def test_tar_rejects_links_and_extraction_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path = tmp_path / "bundle.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        member = tarfile.TarInfo("horizon/link")
        member.type = tarfile.SYMTYPE
        member.linkname = "../outside"
        archive.addfile(member)
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    with pytest.raises(IntegrityError, match="link"):
        extract_horizon_bundle(archive_path, staging_dir)
    with tarfile.open(archive_path, "w:gz") as archive:
        member = tarfile.TarInfo("horizon/big")
        member.size = 20
        archive.addfile(member, io.BytesIO(b"a" * 20))
    monkeypatch.setattr("nostalgia.horizon.archive.MAX_EXPANDED_BYTES", 10)
    with pytest.raises(IntegrityError, match="limits"):
        extract_horizon_bundle(archive_path, staging_dir)


def test_cancelled_extract_does_not_write_files(tmp_path: Path) -> None:
    from nostalgia.errors import Cancelled

    archive_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("horizon/file", "content")
    cancel_token = CancelToken()
    cancel_token.cancel()
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    with pytest.raises(Cancelled):
        extract_horizon_bundle(archive_path, staging_dir, cancel_token)
    assert not list(staging_dir.iterdir())
