"""Đóng vai giao diện: đi trọn một vòng chỉ bằng `nostalgia.api`.

File này đi trọn vòng đời chỉ bằng những gì façade cho ra. Ngoài nó chỉ có hai thứ, và cả
hai đều là đồ dùng của TEST chứ không phải của giao diện: máy chủ giả, và bộ khách HTTP tin
chứng chỉ tự ký. Nếu một ngày vòng đời này không làm được qua façade nữa thì test ở đây gãy
trước khi giao diện thật gãy.
"""

from __future__ import annotations

import ssl
from pathlib import Path

import pytest

from fake_mojang import JAVA_BODY, VERSION_ID, publish
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Instance, Launcher
from nostalgia.errors import AccountError, InstanceError
from nostalgia.net.http import HttpClient
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform

LINUX = Platform(os_name="linux", os_arch="x64", os_version="6.8.0")


def make_launcher(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    *,
    java_body: bytes = JAVA_BODY,
) -> Launcher:
    """Trỏ façade sang máy chủ cục bộ — đúng điểm tiêm mà giao diện thật cũng sẽ dùng."""
    certificate, _key = certificate_pair
    trusting = ssl.create_default_context(cafile=str(certificate))

    def make_http_client() -> HttpClient:
        return HttpClient(timeout_seconds=5.0, tls_context=trusting)

    return Launcher(
        paths=DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config"),
        platform=LINUX,
        endpoints=publish(server, server_state, java_body=java_body),
        make_http_client=make_http_client,
    )


def test_the_whole_round_trip_works_through_the_facade_alone(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Cài → tạo bản chơi → thêm tài khoản → chơi → dừng, không chạm module nội bộ nào."""
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)

    report = launcher.install_version(VERSION_ID)
    assert report.version_meta.version_id == VERSION_ID
    assert launcher.list_installed_versions() == (VERSION_ID,)

    launcher.create_instance(Instance(instance_id="thu", version_id=VERSION_ID))
    assert [instance.instance_id for instance in launcher.list_instances()] == ["thu"]

    account = launcher.add_offline_account("Jun")
    assert account.player_uuid
    assert [account.player_name for account in launcher.list_accounts()] == ["Jun"]

    assert launcher.diagnose_version(VERSION_ID).is_healthy

    lines: list[str] = []
    game = launcher.launch_instance("thu", "Jun", on_output=lines.append)
    assert game.wait(timeout=30) == 0
    assert any("fake java" in line for line in lines)


def test_progress_reaches_the_caller_without_anything_being_printed(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Lõi không in ra màn hình — giao diện đồ hoạ không có màn hình để in."""
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    steps: list[object] = []

    launcher.install_version(VERSION_ID, on_progress=steps.append)

    assert steps, "phải báo tiến độ qua callback"
    assert capsys.readouterr().out == ""


def test_the_facade_refuses_clearly_instead_of_returning_none(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Trả `None` là đẩy cho giao diện tự đoán; ném lỗi có tên là hợp đồng rõ ràng."""
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)

    with pytest.raises(InstanceError):
        launcher.launch_instance("khong-co", "Jun")
    with pytest.raises(AccountError):
        launcher.remove_account("khong-co")


def test_removing_an_instance_through_the_facade_keeps_the_worlds(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher.create_instance(Instance(instance_id="cua-toi", version_id=VERSION_ID))
    world = launcher.paths.instance_dir("cua-toi") / "saves"
    world.mkdir(parents=True, exist_ok=True)
    (world / "level.dat").write_bytes(b"x")

    left_behind = launcher.remove_instance("cua-toi")

    assert launcher.list_instances() == ()
    assert (left_behind / "saves" / "level.dat").exists()


def test_two_launchers_can_work_on_two_profiles_at_once(tmp_path: Path) -> None:
    """Giao diện phải mở được hai profile song song — đó là lý do không có trạng thái toàn cục.

    Dựng bằng `for_data_dir` chứ không tự ghép `DataPaths`: đó là đường mà giao diện sẽ đi,
    và nó cố tình ngắn để danh sách module giao diện được chạm không phải nới ra.
    """
    first = Launcher.for_data_dir(tmp_path / "a")
    second = Launcher.for_data_dir(tmp_path / "b")

    first.add_offline_account("Mot")
    second.add_offline_account("Hai")

    assert [account.player_name for account in first.list_accounts()] == ["Mot"]
    assert [account.player_name for account in second.list_accounts()] == ["Hai"]


def test_the_game_process_never_exposes_the_raw_subprocess(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """`Popen` lọt ra ngoài là buộc giao diện phải biết về `subprocess`."""
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher.install_version(VERSION_ID)
    launcher.create_instance(Instance(instance_id="thu", version_id=VERSION_ID))
    launcher.add_offline_account("Jun")

    game = launcher.launch_instance("thu", "Jun")
    try:
        public_names = [name for name in dir(game) if not name.startswith("_")]
        assert sorted(public_names) == ["exit_code", "is_running", "pid", "stop", "wait"]
    finally:
        game.stop(grace_seconds=0.5)


def test_launching_refreshes_a_stale_microsoft_token(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Vé cũ phải được làm mới TRƯỚC khi game chạy, không phải để game tự báo lỗi."""
    import fake_microsoft
    from nostalgia.account.model import MICROSOFT, Account
    from nostalgia.account.store import find_account, save_accounts

    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    auth_endpoints = fake_microsoft.publish(server, server_state)
    launcher = Launcher(
        paths=launcher.paths,
        platform=launcher.platform,
        endpoints=launcher.endpoints,
        auth_endpoints=auth_endpoints,
        make_http_client=launcher.make_http_client,
    )
    launcher.install_version(VERSION_ID)
    launcher.create_instance(Instance(instance_id="thu", version_id=VERSION_ID))
    save_accounts(
        launcher.paths.accounts_json,
        (
            Account(
                player_name="Notch",
                player_uuid="b50ad385-829d-3141-a216-7e7d7539ba7f",
                account_kind=MICROSOFT,
                access_token="ve-cu",
                refresh_token=fake_microsoft.REFRESH_TOKEN,
                expires_at=1.0,
            ),
        ),
    )

    game = launcher.launch_instance("thu", "Notch", client_id="ma-ung-dung")
    try:
        saved = find_account(launcher.list_accounts(), "Notch")
        assert saved is not None
        assert saved.access_token != "ve-cu", "phải làm mới trước khi chạy"
        assert saved.expires_at > 1.0
    finally:
        game.stop(grace_seconds=0.5)


def test_launching_without_a_java_runtime_says_so(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Thiếu bản Java thì báo ngay, chứ không để lỗi hiện ra ở chỗ chẳng liên quan."""
    import shutil

    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher.install_version(VERSION_ID)
    launcher.create_instance(Instance(instance_id="thu", version_id=VERSION_ID))
    launcher.add_offline_account("Jun")
    shutil.rmtree(launcher.paths.runtime_dir)

    with pytest.raises(InstanceError, match="Java"):
        launcher.launch_instance("thu", "Jun")
