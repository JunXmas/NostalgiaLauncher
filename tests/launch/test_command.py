"""Dựng lệnh java: kiểm 100% offline, đổi hệ điều hành chỉ là đổi một đối số."""

from __future__ import annotations

from pathlib import Path

import pytest

from nostalgia.account.model import MICROSOFT, Account, to_player_profile
from nostalgia.account.offline import build_offline_account, offline_uuid
from nostalgia.errors import VersionError
from nostalgia.launch.command import (
    LOG4SHELL_MITIGATION,
    START_ON_FIRST_THREAD,
    LaunchCommand,
    LaunchOptions,
    build_launch_command,
)
from nostalgia.launch.tuning import JvmTuning
from nostalgia.model.json_value import JsonValue
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform
from nostalgia.version.inherit import resolve_inheritance
from nostalgia.version.meta import VersionMeta, parse_version_meta
from version_fixtures import load_fixture

LINUX = Platform(os_name="linux", os_arch="x64", os_version="6.8.0")
WINDOWS = Platform(os_name="windows", os_arch="x64", os_version="10.0.22631")
MACOS = Platform(os_name="osx", os_arch="arm64", os_version="23.5.0")
PLATFORMS = [LINUX, WINDOWS, MACOS]

FABRIC_ID = "fabric-loader-0.19.3-1.21.4"
VERSION_IDS = ["1.8.9", "1.12.2", "1.20.1", "1.21.4", FABRIC_ID]

PATHS = DataPaths(data_dir=Path("/kho/data"), config_dir=Path("/kho/config"))
GAME_DIR = Path("/kho/game")
JAVA_BINARY = Path("/kho/runtime/jre/bin/java")
SNAPSHOT = Path(__file__).resolve().parents[1] / "fixture" / "launch" / "1.20.1-linux.txt"


def meta_for(version_id: str) -> VersionMeta:
    """Bản Fabric phải trộn kế thừa trước, đúng như lúc chạy thật."""
    if version_id == FABRIC_ID:
        return parse_version_meta(resolve_inheritance(FABRIC_ID, _load_raw))
    return parse_version_meta(load_fixture(version_id))


def _load_raw(version_id: str) -> JsonValue:
    return load_fixture(version_id)


def build(
    version_id: str,
    platform: Platform = LINUX,
    *,
    options: LaunchOptions | None = None,
    tuning: JvmTuning | None = None,
    virtual_assets_dir: Path | None = None,
) -> LaunchCommand:
    return build_launch_command(
        meta_for(version_id),
        platform,
        PATHS,
        to_player_profile(build_offline_account("Jun")),
        JAVA_BINARY,
        options or LaunchOptions(game_dir=GAME_DIR),
        tuning=tuning,
        virtual_assets_dir=virtual_assets_dir,
    )


@pytest.mark.parametrize("version_id", VERSION_IDS)
@pytest.mark.parametrize("platform", PLATFORMS, ids=lambda p: p.os_name)
def test_no_unsubstituted_placeholder_remains(version_id: str, platform: Platform) -> None:
    """Một test bắt CẢ MỘT LỚP lỗi: mọi biến `${...}` phải biến mất trên mọi đời, mọi hệ.

    Đây là lỗi kinh điển của trình khởi động tự viết — game khởi động rồi thoát ngay với
    thông báo chẳng liên quan gì tới cái tham số câm đã gây ra nó.
    """
    argv = build(version_id, platform).argv
    leftover = [value for value in argv if "${" in value]
    assert not leftover, f"{version_id}/{platform.os_name}: {leftover}"
    assert all(isinstance(value, str) for value in argv)


@pytest.mark.parametrize("version_id", VERSION_IDS)
def test_every_command_can_actually_start_a_jvm(version_id: str) -> None:
    """Ba thứ thiếu một là JVM không chạy: đường dẫn java, `-cp`, và lớp chính."""
    command = build(version_id)
    argv = command.argv
    assert argv[0] == str(JAVA_BINARY)
    assert "-cp" in command.jvm_arguments
    classpath_arg = command.jvm_arguments[command.jvm_arguments.index("-cp") + 1]
    assert str(PATHS.libraries_dir) in classpath_arg
    assert command.main_class in argv
    assert argv.index(command.main_class) > argv.index("-cp")


def test_the_launcher_supplies_what_old_versions_leave_out() -> None:
    """JSON đời ≤1.12 không có khoá `arguments.jvm` — thiếu ba cờ này là game không chạy."""
    command = build("1.8.9")
    joined = " ".join(command.jvm_arguments)
    assert f"-Djava.library.path={PATHS.natives_dir('1.8.9')}" in joined
    assert "-cp" in command.jvm_arguments
    assert LOG4SHELL_MITIGATION in command.jvm_arguments


def test_old_versions_on_macos_get_the_lwjgl2_flag() -> None:
    """LWJGL 2 bắt buộc `-XstartOnFirstThread`; thiếu là cửa sổ không bao giờ hiện."""
    assert START_ON_FIRST_THREAD in build("1.8.9", MACOS).jvm_arguments
    assert START_ON_FIRST_THREAD not in build("1.8.9", LINUX).jvm_arguments


def test_new_versions_bring_that_flag_themselves_and_it_is_not_added_twice() -> None:
    macos_arguments = build("1.20.1", MACOS).jvm_arguments
    assert macos_arguments.count(START_ON_FIRST_THREAD) == 1
    assert macos_arguments.count("-cp") == 1, "thêm `-cp` lần hai là ghi đè classpath thật"


def test_the_log4shell_flag_is_on_every_version() -> None:
    """Mojang đã bổ sung ngược `javaVersion` vào cả JSON đời cũ, nên không còn dấu hiệu nào
    đáng tin để đoán tuổi bản game. Cờ này vô hại với log4j mới, nên thêm luôn."""
    for version_id in VERSION_IDS:
        assert LOG4SHELL_MITIGATION in build(version_id).jvm_arguments, version_id


def test_the_uuid_in_the_command_has_no_dashes() -> None:
    argv = build("1.20.1").argv
    uuid_value = argv[argv.index("--uuid") + 1]
    assert uuid_value == offline_uuid("Jun").replace("-", "")
    assert "-" not in uuid_value


def test_the_classpath_separator_follows_the_target_operating_system() -> None:
    """Đây là đối số, không phải trạng thái của máy đang chạy — nhờ vậy kiểm được cả Windows."""
    windows = build("1.20.1", WINDOWS).jvm_arguments
    linux = build("1.20.1", LINUX).jvm_arguments
    assert ";" in windows[windows.index("-cp") + 1]
    assert ":" in linux[linux.index("-cp") + 1]


def test_demo_mode_reaches_both_argument_formats() -> None:
    demo = LaunchOptions(game_dir=GAME_DIR, is_demo=True)
    assert "--demo" in build("1.20.1", options=demo).game_arguments
    assert "--demo" in build("1.8.9", options=demo).game_arguments
    assert "--demo" not in build("1.20.1").game_arguments
    assert "--demo" not in build("1.8.9").game_arguments


def test_a_custom_window_size_appears_only_when_both_numbers_are_given() -> None:
    sized = LaunchOptions(game_dir=GAME_DIR, window_width=1280, window_height=720)
    arguments = build("1.20.1", options=sized).game_arguments
    assert arguments[arguments.index("--width") + 1] == "1280"
    assert arguments[arguments.index("--height") + 1] == "720"

    half = LaunchOptions(game_dir=GAME_DIR, window_width=1280)
    assert "--width" not in build("1.20.1", options=half).game_arguments


def test_quick_play_arguments_stay_out_while_the_feature_is_off() -> None:
    """Chúng dùng biến ta chưa hỗ trợ; lọt vào là lệnh còn `${` và bị chặn."""
    assert "--quickPlayPath" not in build("1.21.4").game_arguments


def test_old_versions_get_the_empty_user_properties_object() -> None:
    """Đời ≤1.7 chờ một đối tượng JSON; bỏ trống thì game đọc tham số kế tiếp làm giá trị."""
    arguments = build("1.8.9").game_arguments
    assert arguments[arguments.index("--userProperties") + 1] == "{}"


def test_legacy_assets_can_be_pointed_at_the_name_tree(tmp_path: Path) -> None:
    """Đời ≤1.7 đọc asset theo TÊN, nên `--assetsDir` phải trỏ vào cây tên, không vào kho."""
    virtual_dir = tmp_path / "virtual" / "legacy"
    arguments = build("1.8.9", virtual_assets_dir=virtual_dir).game_arguments
    assert arguments[arguments.index("--assetsDir") + 1] == str(virtual_dir)
    assert build("1.8.9").game_arguments[
        build("1.8.9").game_arguments.index("--assetsDir") + 1
    ] == str(PATHS.assets_dir)


def test_the_fabric_command_runs_the_loader_but_keeps_the_vanilla_jar() -> None:
    command = build(FABRIC_ID)
    assert command.main_class.startswith("net.fabricmc")
    classpath_arg = command.jvm_arguments[command.jvm_arguments.index("-cp") + 1]
    assert "1.21.4.jar" in classpath_arg, "jar là của bản vanilla, không phải của loader"
    # `${version_name}` là mã bản SỞ HỮU jar, không phải id loader: Forge dùng nó trong
    # `-DignoreList=…,${version_name}.jar` để bỏ client jar khỏi module path. Đặt id loader vào
    # thì Forge 1.20.1 chết ngay lúc khởi động với "Modules minecraft and _1._20._1 export
    # package net.minecraft.data" (đã gặp thật).
    assert command.game_arguments[command.game_arguments.index("--version") + 1] == "1.21.4"


def test_memory_flags_come_before_the_version_flags_so_the_version_wins() -> None:
    command = build("1.20.1", tuning=JvmTuning(max_heap_megabytes=4096, min_heap_megabytes=1024))
    assert "-Xmx4096M" in command.jvm_arguments
    assert command.jvm_arguments.index("-Xmx4096M") < command.jvm_arguments.index("-cp")


def test_extra_jvm_flags_land_after_the_memory_flags() -> None:
    tuning = JvmTuning(extra_arguments=("-Xmx8G", "-XX:+UseZGC"))
    arguments = build("1.20.1", tuning=tuning).jvm_arguments
    assert arguments.index("-Xmx8G") > arguments.index("-Xmx2048M"), "cờ người dùng phải thắng"
    assert "-XX:+UseZGC" in arguments


def test_a_real_token_is_masked_when_the_command_is_printed() -> None:
    """Lệnh khởi động là thứ người dùng hay dán vào báo lỗi."""
    account = Account(
        player_name="Jun", player_uuid="0" * 32, account_kind=MICROSOFT, access_token="ve-rat-dai"
    )
    command = build_launch_command(
        meta_for("1.20.1"),
        LINUX,
        PATHS,
        to_player_profile(account),
        JAVA_BINARY,
        LaunchOptions(game_dir=GAME_DIR),
    )
    assert "ve-rat-dai" in command.argv
    assert "ve-rat-dai" not in command.masked_argv()
    assert "***" in command.masked_argv()


def test_the_placeholder_token_of_offline_accounts_is_not_masked() -> None:
    """Che cả vé giả `"0"` sẽ che nhầm mọi tham số có giá trị 0."""
    command = build("1.20.1")
    assert command.masked_argv() == command.argv


def test_an_unknown_variable_stops_the_launch_instead_of_producing_a_broken_command() -> None:
    version_dict = dict(load_fixture("1.20.1"))
    version_dict["minecraftArguments"] = "--kho ${bien_la}"
    with pytest.raises(VersionError, match=r"\$\{bien_la\}"):
        build_launch_command(
            parse_version_meta(version_dict),
            LINUX,
            PATHS,
            to_player_profile(build_offline_account("Jun")),
            JAVA_BINARY,
            LaunchOptions(game_dir=GAME_DIR),
        )


def test_the_command_matches_the_approved_snapshot() -> None:
    """Mọi thay đổi ngoài ý muốn trong lệnh sẽ lộ ra ở diff của PR, không lọt êm."""
    argv = build("1.20.1").argv
    approved = SNAPSHOT.read_text(encoding="utf-8").splitlines()
    assert list(argv) == approved
