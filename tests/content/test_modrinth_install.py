"""Cài từ Modrinth: phụ thuộc bắt buộc, sổ theo dõi, vòng phụ thuộc, từ chối mod trên vanilla."""

from __future__ import annotations

from pathlib import Path

import pytest

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from modrinth_fixture import (
    FABRIC_API,
    LOOPEE,
    LOOPER,
    SODIUM,
    fabric_target,
    make_content_launcher,
)
from nostalgia.api import Instance
from nostalgia.content.model import Project
from nostalgia.errors import ContentError


def test_install_pulls_required_dependency_and_records_the_ledger(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    sodium = launcher.search_content(target, "mod").hits[0]

    report = launcher.install_content(target, sodium)

    assert [v.project_id for v in report.installed] == [SODIUM, FABRIC_API]
    # Bản `release` được ưu tiên hơn beta dù beta đứng trước; bản forge bị loại.
    assert report.installed[0].version_type == "release"
    installed = launcher.list_installed_content(target, "mod")
    assert {(m.file_name, m.title, m.enabled) for m in installed} == {
        (f"{SODIUM}.jar", "Sodium", True),
        (f"{FABRIC_API}.jar", "", True),
    }

    # Cài lần hai: phụ thuộc đã có trong sổ nên không hỏi lại Modrinth về nó.
    launcher.install_content(target, sodium)
    assert server_state.request_count(f"/modrinth/project/{FABRIC_API}/version") == 1


def test_dependency_cycles_terminate(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:

    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    looper = Project(
        project_id=LOOPER,
        project_slug="a",
        title="A",
        description="",
        author="",
        content_kind="mod",
        icon_url="",
        downloads=0,
        follows=0,
        loaders=("fabric",),
    )

    report = launcher.install_content(target, looper)

    assert sorted(v.project_id for v in report.installed) == [LOOPER, LOOPEE]
    assert server_state.request_count(f"/modrinth/project/{LOOPER}/version") == 1


def test_mod_on_vanilla_instance_is_refused_before_any_request(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    launcher.install_version(VERSION_ID)
    launcher.create_instance(Instance(instance_id="van", version_id=VERSION_ID))
    target = launcher.describe_content_target("van")
    assert target.loader_kind == "vanilla"
    sodium = launcher.search_content(target, "mod").hits[0]

    with pytest.raises(ContentError, match="không có mod loader"):
        launcher.install_content(target, sodium)
    assert server_state.request_count(f"/modrinth/project/{SODIUM}/version") == 0


def test_concurrent_installs_into_one_folder_keep_every_ledger_entry(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Hàng đợi cài nhiều mod, hoặc cài từ thẻ và từ hộp thoại cùng lúc: hai lượt đọc sổ cũ rồi
    ghi đè nhau thì mục của lượt trước mất (mod có trên đĩa nhưng launcher không biết nguồn)."""
    import threading

    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    sodium = launcher.search_content(target, "mod").hits[0]
    looper = Project(
        project_id=LOOPER,
        project_slug="a",
        title="A",
        description="",
        author="",
        content_kind="mod",
        icon_url="",
        downloads=0,
        follows=0,
        loaders=("fabric",),
    )
    start = threading.Barrier(2)
    errors: list[BaseException] = []

    def install(project: Project) -> None:
        start.wait()
        try:
            launcher.install_content(target, project)
        except BaseException as error:
            errors.append(error)

    workers = [threading.Thread(target=install, args=(p,)) for p in (sodium, looper)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    assert not errors
    installed = {m.project_id for m in launcher.list_installed_content(target, "mod")}
    assert {SODIUM, FABRIC_API, LOOPER, LOOPEE} <= installed
