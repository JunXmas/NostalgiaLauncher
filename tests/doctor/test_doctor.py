"""Soi bản cài: chỉ đúng mắt xích hỏng, và phân biệt chặn với cảnh báo."""

from __future__ import annotations

from pathlib import Path

import pytest

from install_fixture import (
    ASSET_BODY,
    CLIENT_BODY,
    VERSION_ID,
    build_install,
    digest,
)
from nostalgia.doctor import (
    ASSET,
    ASSET_INDEX,
    CLIENT_JAR,
    JAVA,
    LIBRARY,
    MISSING,
    NATIVES,
    NOT_EXECUTABLE,
    WRONG_HASH,
    WRONG_SIZE,
    Diagnosis,
    diagnose,
    remove_broken_files,
)
from nostalgia.errors import Cancelled
from nostalgia.model.asset_index import parse_asset_index
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.files import set_executable
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform
from nostalgia.version.meta import parse_version_meta
from version_fixtures import load_fixture

LINUX = Platform(os_name="linux", os_arch="x64", os_version="6.8.0")


def run(
    tmp_path: Path,
    *,
    remove: Path | None = None,
    java_binary: Path | None = None,
    verify_hashes: bool = False,
    with_index: bool = True,
    cancel_token: CancelToken | None = None,
) -> tuple[Diagnosis, DataPaths]:
    paths, version_dict, index_document = build_install(tmp_path)
    if remove is not None:
        remove.unlink()
    return diagnose(
        parse_version_meta(version_dict),
        LINUX,
        paths,
        asset_index=parse_asset_index(index_document) if with_index else None,
        java_binary=java_binary,
        verify_hashes=verify_hashes,
        cancel_token=cancel_token,
    ), paths


def test_a_complete_installation_is_healthy(tmp_path: Path) -> None:
    diagnosis, _paths = run(tmp_path)
    assert diagnosis.findings == ()
    assert diagnosis.is_healthy
    assert diagnosis.checked == 6, (
        "client + jar thư viện + jar natives + file .so đã bung + chỉ mục + một asset"
    )


def test_a_missing_client_jar_blocks_the_launch(tmp_path: Path) -> None:
    paths = DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")
    diagnosis, _paths = run(tmp_path, remove=paths.version_jar(VERSION_ID))
    assert not diagnosis.is_healthy
    assert [finding.part for finding in diagnosis.fatal_findings] == [CLIENT_JAR]
    assert diagnosis.fatal_findings[0].problem == MISSING


def test_a_missing_library_blocks_the_launch(tmp_path: Path) -> None:
    paths = DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")
    diagnosis, _paths = run(tmp_path, remove=paths.libraries_dir / "org/thu/vien/1.0/vien-1.0.jar")
    assert [finding.part for finding in diagnosis.fatal_findings] == [LIBRARY]


def test_a_missing_native_file_blocks_the_launch(tmp_path: Path) -> None:
    """Thiếu `.so` thì game khởi động rồi sập ngay khi mở cửa sổ."""
    paths = DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")
    diagnosis, _paths = run(tmp_path, remove=paths.natives_dir(VERSION_ID) / "libthu.so")
    assert [finding.part for finding in diagnosis.fatal_findings] == [NATIVES]


def test_the_excluded_manifest_is_not_expected_on_disk(tmp_path: Path) -> None:
    """`doctor` dùng chính luật lọc của bộ giải nén, nên không đòi file bị loại."""
    diagnosis, _paths = run(tmp_path)
    assert all("MANIFEST" not in str(finding.path) for finding in diagnosis.findings)


def test_a_missing_asset_is_only_a_warning(tmp_path: Path) -> None:
    """Game vẫn chạy, chỉ mất một âm thanh. Chặn ở đây là làm phiền vô cớ."""
    paths = DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")
    diagnosis, _paths = run(tmp_path, remove=paths.asset_object(digest(ASSET_BODY)))
    assert diagnosis.is_healthy
    assert [finding.part for finding in diagnosis.warnings] == [ASSET]


def test_a_missing_asset_index_does_block(tmp_path: Path) -> None:
    """Không có chỉ mục thì không kiểm được gì, và đời cũ cần nó để dựng cây tên."""
    paths = DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")
    diagnosis, _paths = run(tmp_path, remove=paths.asset_index_json("kt"))
    assert [finding.part for finding in diagnosis.fatal_findings] == [ASSET_INDEX]


def test_a_file_of_the_wrong_size_is_caught_without_hashing(tmp_path: Path) -> None:
    paths, version_dict, _index_document = build_install(tmp_path)
    paths.version_jar(VERSION_ID).write_bytes(CLIENT_BODY + b"thua")

    diagnosis = diagnose(parse_version_meta(version_dict), LINUX, paths)

    assert diagnosis.fatal_findings[0].problem == WRONG_SIZE


def test_only_hash_checking_catches_a_file_edited_in_place(tmp_path: Path) -> None:
    """Sửa đúng bằng số byte cũ là cách hỏng mà kiểm kích thước không bao giờ thấy."""
    paths, version_dict, _index_document = build_install(tmp_path)
    edited = bytearray(CLIENT_BODY)
    edited[0] ^= 0xFF
    paths.version_jar(VERSION_ID).write_bytes(bytes(edited))
    version_meta = parse_version_meta(version_dict)

    assert diagnose(version_meta, LINUX, paths).is_healthy

    deep = diagnose(version_meta, LINUX, paths, verify_hashes=True)
    assert not deep.is_healthy
    assert deep.fatal_findings[0].problem == WRONG_HASH


def test_the_java_binary_must_exist_and_be_executable(tmp_path: Path) -> None:
    java_binary = tmp_path / "java"
    diagnosis, _paths = run(tmp_path, java_binary=java_binary)
    assert [finding.part for finding in diagnosis.fatal_findings] == [JAVA]

    java_binary.write_bytes(b"#!/bin/sh\n")
    java_binary.chmod(0o644)
    diagnosis, _paths = run(tmp_path, java_binary=java_binary)
    assert diagnosis.fatal_findings[0].problem == NOT_EXECUTABLE

    set_executable(java_binary)
    diagnosis, _paths = run(tmp_path, java_binary=java_binary)
    assert diagnosis.is_healthy


def test_repair_removes_only_the_files_that_exist_and_are_wrong(tmp_path: Path) -> None:
    """Thứ đang thiếu thì không có gì để xoá; xoá nhầm khi sửa chữa còn tệ hơn hỏng."""
    paths, version_dict, _index_document = build_install(tmp_path)
    paths.version_jar(VERSION_ID).write_bytes(b"sai")
    missing_library = paths.libraries_dir / "org/thu/vien/1.0/vien-1.0.jar"
    missing_library.unlink()

    diagnosis = diagnose(parse_version_meta(version_dict), LINUX, paths)
    removed = remove_broken_files(diagnosis)

    assert removed == (paths.version_jar(VERSION_ID),)
    assert not paths.version_jar(VERSION_ID).exists()
    assert not missing_library.exists()


def test_repairing_twice_is_harmless(tmp_path: Path) -> None:
    paths, version_dict, _index = build_install(tmp_path)
    paths.version_jar(VERSION_ID).write_bytes(b"sai")
    diagnosis = diagnose(parse_version_meta(version_dict), LINUX, paths)

    assert remove_broken_files(diagnosis) == (paths.version_jar(VERSION_ID),)
    assert remove_broken_files(diagnosis) == ()


def test_the_scan_can_be_cancelled(tmp_path: Path) -> None:
    cancel_token = CancelToken()
    cancel_token.cancel()
    with pytest.raises(Cancelled):
        run(tmp_path, cancel_token=cancel_token)


def test_nothing_installed_at_all_is_reported_part_by_part(tmp_path: Path) -> None:
    """Trên bản thật 1.20.1: mọi thứ đều thiếu, và số mục soi khớp với kế hoạch cài."""
    paths = DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")
    version_meta = parse_version_meta(load_fixture("1.20.1"))

    diagnosis = diagnose(version_meta, LINUX, paths)

    assert not diagnosis.is_healthy
    assert diagnosis.checked == len(diagnosis.findings), "chưa cài gì thì mục nào cũng hỏng"
    assert {finding.part for finding in diagnosis.findings} == {CLIENT_JAR, LIBRARY, ASSET_INDEX}
    assert all(finding.problem == MISSING for finding in diagnosis.findings)


def test_repair_does_not_delete_a_file_that_appeared_after_the_scan(tmp_path: Path) -> None:
    """Một lượt cài khác có thể kết thúc giữa lúc soi và lúc sửa.

    Kết quả soi là ảnh chụp của quá khứ. Xoá theo nó mà không phân biệt "thiếu" với "sai" sẽ
    xoá đúng file vừa được tải xong, và lần chạy sau lại phải tải lại từ đầu.
    """
    paths, version_dict, _index = build_install(tmp_path)
    client_jar = paths.version_jar(VERSION_ID)
    client_jar.unlink()
    diagnosis = diagnose(parse_version_meta(version_dict), LINUX, paths)
    assert diagnosis.fatal_findings[0].problem == MISSING

    client_jar.write_bytes(CLIENT_BODY)
    removed = remove_broken_files(diagnosis)

    assert removed == ()
    assert client_jar.read_bytes() == CLIENT_BODY
