"""Đổi mod qua HTTPS thật, giữ bản cũ/ledger khi hỏng và hoàn tác có kiểm dữ liệu."""

from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from mod_version_fixture import releases
from modrinth_fixture import fabric_target, make_content_launcher
from nostalgia.errors import ContentError, NetworkError
from nostalgia.storage.directory_swap import tree_hash


@pytest.mark.parametrize("enabled", [True, False])
def test_switch_and_undo_restore_the_old_file_ledger_and_enabled_state(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    enabled: bool,
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    project = launcher.search_content(target, "mod").hits[0]
    releases(server, server_state)
    launcher.install_content(target, project, version_id="old")
    launcher.set_content_enabled(target, "mod", "sodium-old.jar", enabled)
    (target.game_dir / "saves").mkdir()
    (target.game_dir / "saves/world.txt").write_text("keep this world")
    before = tree_hash(target.game_dir / "mods")
    receipt = launcher.swap_mod_version(target.instance_id, "sodium-old.jar", "new", lambda: False)
    installed = launcher.list_installed_content(target, "mod")
    assert (
        len(installed) == 1 and installed[0].version_id == "new" and installed[0].enabled is enabled
    )
    assert not (target.game_dir / "mods/sodium-old.jar").exists()
    assert launcher.latest_mod_version_change(target.instance_id) == receipt
    launcher.scan_installed_content(target, "mod")
    launcher.undo_mod_version(target.instance_id, receipt, lambda: False)
    assert tree_hash(target.game_dir / "mods") == before
    assert (target.game_dir / "saves/world.txt").read_text() == "keep this world"
    assert not launcher.latest_mod_version_change(target.instance_id)


@pytest.mark.parametrize("failure", ["hash", "running", "late_running", "rename"])
def test_failed_swap_keeps_every_original_byte(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    project = launcher.search_content(target, "mod").hits[0]
    releases(server, server_state, broken=failure == "hash")
    launcher.install_content(target, project, version_id="old")
    before = tree_hash(target.game_dir / "mods")
    calls = 0

    def running() -> bool:
        nonlocal calls
        calls += 1
        return failure == "running" or (failure == "late_running" and calls > 1)

    replace_path = Path.replace

    def replace_stage(path: Path, destination: Path) -> Path:
        if failure == "rename" and path.name == "mods" and ".nostalgia-version-" in str(path):
            raise PermissionError("fixture locked files")
        return replace_path(path, destination)

    monkeypatch.setattr(Path, "replace", replace_stage)
    with pytest.raises((ContentError, NetworkError, PermissionError)):
        launcher.swap_mod_version(target.instance_id, "sodium-old.jar", "new", running)
    assert tree_hash(target.game_dir / "mods") == before
    assert not launcher.latest_mod_version_change(target.instance_id)


def test_undo_refuses_to_overwrite_changes_made_after_swap(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    project = launcher.search_content(target, "mod").hits[0]
    releases(server, server_state)
    launcher.install_content(target, project, version_id="old")
    receipt = launcher.swap_mod_version(target.instance_id, "sodium-old.jar", "new", lambda: False)
    (target.game_dir / "mods/user-custom.jar").write_bytes(b"user change")
    before = tree_hash(target.game_dir / "mods")
    with pytest.raises(ContentError, match="thay đổi"):
        launcher.undo_mod_version(target.instance_id, receipt, lambda: False)
    assert tree_hash(target.game_dir / "mods") == before
