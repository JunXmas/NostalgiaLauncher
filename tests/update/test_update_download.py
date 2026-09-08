"""Tải gói cập nhật qua máy chủ HTTPS giả: đúng băm thì cài, sai băm thì xoá và từ chối, thiếu
SHA256SUMS thì từ chối; GitHub chuyển hướng 302 tới CDN vẫn tải được; zip thoát thư mục bị chặn."""

from __future__ import annotations

import hashlib
import io
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import IntegrityError, UnsafePathError, UpdateError
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.update.download import download_bundle, unpack_bundle
from nostalgia.update.release import ReleaseAsset
from release_fixture import RELEASE_VERSION, make_bundle, make_launcher, publish_release


def test_check_download_and_stage_follow_the_whole_path(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    bundle = make_bundle("moi")
    asset_name = publish_release(server, server_state, bundle)
    launcher = make_launcher(server, tmp_path, certificate_pair[0])

    release = launcher.check_launcher_update()
    assert release is not None and release.launcher_version == RELEASE_VERSION
    seen: list[int] = []
    staged = launcher.download_launcher_update(
        release, on_progress=lambda progress: seen.append(progress.done)
    )
    assert staged.launcher_version == RELEASE_VERSION
    assert (staged.bundle_dir / "lib" / "core.txt").read_text() == "moi"
    assert staged.bundle_dir.name == "Nostalgia", "bỏ lớp thư mục bọc của zip"
    assert seen and seen[-1] == len(bundle)
    assert (launcher.paths.updates_dir / asset_name).is_file()
    assert server_state.request_count(f"/cdn/{asset_name}") == 1

    launcher.download_launcher_update(release)
    assert server_state.request_count(f"/cdn/{asset_name}") == 1, (
        "đã có file đúng băm thì không tải lại"
    )
    with pytest.raises(UpdateError, match="mã nguồn"):
        launcher.apply_launcher_update(staged)


def test_wrong_hash_and_missing_sums_are_refused(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    bundle = make_bundle("gia")
    asset_name = publish_release(server, server_state, bundle)
    launcher = make_launcher(server, tmp_path, certificate_pair[0])
    release = launcher.check_launcher_update()
    assert release is not None
    server_state.add("/sums", f"{'0' * 64}  {asset_name}\n".encode())
    with pytest.raises(IntegrityError):
        launcher.download_launcher_update(release)
    assert not (launcher.paths.updates_dir / asset_name).exists(), "file sai băm phải bị xoá"
    assert not list(launcher.paths.updates_dir.glob("*.part"))

    publish_release(server, server_state, bundle, sums=False)
    release = launcher.check_launcher_update()
    assert release is not None
    with pytest.raises(UpdateError, match="SHA256SUMS"):
        launcher.download_launcher_update(release)


def test_older_or_prerelease_or_foreign_platform_is_not_an_update(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    import json

    launcher = make_launcher(server, tmp_path, certificate_pair[0])
    server_state.add("/releases/latest", json.dumps({"tag_name": "v0.0.1", "assets": []}).encode())
    assert launcher.check_launcher_update() is None, "bản cũ hơn"
    server_state.add(
        "/releases/latest",
        json.dumps(
            {
                "tag_name": "v9.9.9",
                "assets": [
                    {
                        "name": "nostalgia-9.9.9-windows-x64.zip",
                        "browser_download_url": server.url("/x"),
                    }
                ],
            }
        ).encode(),
    )
    assert launcher.check_launcher_update() is None, "không có gói cho linux"
    server_state.add("/releases/latest", b"Not Found", status=404)
    assert launcher.check_launcher_update() is None, "chưa có bản phát hành nào"


def test_zip_slip_is_rejected_and_direct_download_verifies(tmp_path: Path) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../ngoai.txt", "thoát")
    evil = tmp_path / "evil.zip"
    evil.write_bytes(buffer.getvalue())
    with pytest.raises(UnsafePathError):
        unpack_bundle(evil, tmp_path / "bung")
    assert not (tmp_path / "ngoai.txt").exists()

    class NoNetwork(HttpClient):
        def stream(
            self,
            url: str,
            write: Callable[[bytes], None],
            *,
            expected_size: int | None = None,
            max_bytes: int | None = None,
            cancel_token: CancelToken | None = None,
        ) -> int:
            del url, expected_size, max_bytes, cancel_token  # chữ ký phải khớp lớp cha
            write(b"noi dung")
            return 8

    release_asset = ReleaseAsset("a.zip", "https://x/a.zip", 8)
    good = hashlib.sha256(b"noi dung").hexdigest()
    path = download_bundle(NoNetwork(), release_asset, good, tmp_path / "updates")
    assert path.read_bytes() == b"noi dung"
