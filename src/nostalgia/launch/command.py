"""Dựng lệnh java hoàn chỉnh. Không chạy gì — chỉ trả về danh sách tham số.

Tách hẳn khỏi việc chạy tiến trình, nhờ vậy toàn bộ phần khó nhất của một trình khởi động
được kiểm **100% offline**: đổi hệ điều hành là đổi một đối số, không phải đổi máy.

Ba thứ launcher phải TỰ thêm cho đời ≤1.12, vì JSON đời đó không có khoá `arguments.jvm`:

1. `-Djava.library.path` — không có thì game không nạp được thư viện natives.
2. `-cp` — không có thì JVM không tìm thấy lớp nào.
3. `-XstartOnFirstThread` trên macOS — LWJGL 2 bắt buộc, thiếu là cửa sổ không hiện.

Cờ chống Log4Shell được thêm **cho mọi phiên bản**, cố ý. Mojang đã bổ sung ngược khoá
`javaVersion` vào cả JSON của 1.8.9 lẫn 1.12.2, nên trong JSON không còn dấu hiệu nào đáng
tin để đoán tuổi bản game. Cờ này vô hại với log4j ≥ 2.16 (chỉ bị bỏ qua), nên thêm luôn
đáng tin hơn là đoán sai.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from nostalgia import __version__
from nostalgia.account.model import PlayerProfile
from nostalgia.errors import VersionError
from nostalgia.launch.tuning import JvmTuning
from nostalgia.launch.variables import build_launch_variables
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform, classpath_separator
from nostalgia.version.arguments import (
    resolve_argument_values,
    split_legacy_arguments,
    substitute_placeholders,
    unresolved_placeholders,
)
from nostalgia.version.classpath import join_classpath, resolve_classpath
from nostalgia.version.meta import VersionMeta

LAUNCHER_NAME = "nostalgia"
LOG4SHELL_MITIGATION = "-Dlog4j2.formatMsgNoLookups=true"
START_ON_FIRST_THREAD = "-XstartOnFirstThread"
MASK = "***"


@dataclass(frozen=True, slots=True)
class LaunchOptions:
    """Lựa chọn của người chơi cho một lần khởi động."""

    game_dir: Path
    window_width: int | None = None
    window_height: int | None = None
    is_demo: bool = False
    # Vào thẳng thế giới này (tên thư mục trong saves/). Đời < 1.20 không có quick play thì
    # khối tham số không tồn tại trong JSON và game mở bình thường, không lỗi.
    world_folder: str = ""
    # Vào thẳng máy chủ này (`host[:port]`), cũng chỉ 1.20+. Không đi cùng `world_folder`.
    server_address: str = ""

    def __post_init__(self) -> None:
        if self.world_folder and self.server_address:
            message = "chỉ vào thẳng MỘT nơi: thế giới hoặc máy chủ, không cả hai"
            raise ValueError(message)

    @property
    def features(self) -> dict[str, bool]:
        """Cờ tính năng của Mojang, quyết định tham số nào được giữ lại.

        Thiếu một cờ nghĩa là tắt, nên chỉ cần khai những cờ ta thật sự bật. KHÔNG bật
        `has_quick_plays_support`: cờ đó gác `--quickPlayPath ${quickPlayPath}` mà ta không
        cấp biến, sẽ bị `_refuse_unresolved` chặn.
        """
        return {
            "is_demo_user": self.is_demo,
            "has_custom_resolution": self.window_width is not None
            and self.window_height is not None,
            "is_quick_play_singleplayer": bool(self.world_folder),
            "is_quick_play_multiplayer": bool(self.server_address),
        }


@dataclass(frozen=True, slots=True)
class LaunchCommand:
    """Lệnh đã dựng xong, tách theo phần để test đọc được từng phần."""

    java_binary: Path
    jvm_arguments: tuple[str, ...]
    main_class: str
    game_arguments: tuple[str, ...]
    game_dir: Path
    secret_values: frozenset[str] = field(default_factory=frozenset)

    @property
    def argv(self) -> tuple[str, ...]:
        """Đúng thứ tự JVM đòi: cờ máy ảo, rồi lớp chính, rồi tham số của game."""
        return (
            str(self.java_binary),
            *self.jvm_arguments,
            self.main_class,
            *self.game_arguments,
        )

    def masked_argv(self) -> tuple[str, ...]:
        """Bản để in ra hoặc ghi log: vé đăng nhập bị che.

        Lệnh khởi động là thứ người dùng hay dán vào báo lỗi. Không che ở đây thì vé
        Microsoft của họ đi thẳng lên diễn đàn.

        Dùng substring replace thay vì so khớp tuyệt đối: với Minecraft < 1.8, chuỗi
        ``--session token:<access_token>:<uuid>`` chứa token BÊN TRONG giá trị lớn hơn.
        """
        masked: list[str] = []
        for value in self.argv:
            result = value
            for secret in self.secret_values:
                result = result.replace(secret, MASK)
            masked.append(result)
        return tuple(masked)


def build_launch_command(
    version_meta: VersionMeta,
    platform: Platform,
    paths: DataPaths,
    player_profile: PlayerProfile,
    java_binary: Path,
    options: LaunchOptions,
    *,
    tuning: JvmTuning | None = None,
    virtual_assets_dir: Path | None = None,
) -> LaunchCommand:
    """Dựng lệnh khởi động đầy đủ.

    `virtual_assets_dir` chỉ khác `None` với đời ≤1.7, khi chỉ mục asset là kiểu `virtual`
    và game đọc asset theo TÊN. Người gọi truyền vào vì chỉ họ mới đọc chỉ mục; hàm này
    không chạm đĩa.
    """
    natives_dir = paths.natives_dir(version_meta.version_id)
    assets_root = virtual_assets_dir or paths.assets_dir
    variables = build_launch_variables(
        version_meta,
        player_profile,
        game_dir=options.game_dir,
        assets_root=assets_root,
        game_assets_dir=virtual_assets_dir or paths.assets_dir,
        natives_dir=natives_dir,
        libraries_dir=paths.libraries_dir,
        classpath_arg=join_classpath(
            resolve_classpath(version_meta, platform, paths), platform.os_name
        ),
        classpath_separator=classpath_separator(platform.os_name),
        launcher_name=LAUNCHER_NAME,
        launcher_version=__version__,
        window_width=options.window_width,
        window_height=options.window_height,
        quick_play_world=options.world_folder or None,
        quick_play_server=options.server_address or None,
    )

    jvm_arguments = substitute_placeholders(
        _collect_jvm_arguments(version_meta, platform, tuning or JvmTuning()), variables
    )
    game_arguments = substitute_placeholders(
        _collect_game_arguments(version_meta, platform, options), variables
    )
    _refuse_unresolved(version_meta, jvm_arguments + game_arguments)

    return LaunchCommand(
        java_binary=java_binary,
        jvm_arguments=jvm_arguments,
        main_class=version_meta.main_class,
        game_arguments=game_arguments,
        game_dir=options.game_dir,
        secret_values=_secret_values(player_profile),
    )


def _collect_jvm_arguments(
    version_meta: VersionMeta, platform: Platform, tuning: JvmTuning
) -> tuple[str, ...]:
    """Cờ của launcher đứng trước, cờ của bản game đứng sau — bản game thắng khi trùng."""
    launcher_arguments = [LOG4SHELL_MITIGATION, *tuning.to_arguments()]
    from_version = resolve_argument_values(version_meta.jvm_arguments, platform)
    if from_version:
        return (*launcher_arguments, *from_version)
    if platform.os_name == "osx":
        launcher_arguments.append(START_ON_FIRST_THREAD)
    launcher_arguments += [
        "-Djava.library.path=${natives_directory}",
        "-Dminecraft.launcher.brand=${launcher_name}",
        "-Dminecraft.launcher.version=${launcher_version}",
        "-cp",
        "${classpath}",
    ]
    return tuple(launcher_arguments)


def _collect_game_arguments(
    version_meta: VersionMeta, platform: Platform, options: LaunchOptions
) -> tuple[str, ...]:
    if version_meta.minecraft_arguments is not None:
        legacy = split_legacy_arguments(version_meta.minecraft_arguments)
        return (*legacy, "--demo") if options.is_demo else legacy
    return resolve_argument_values(version_meta.game_arguments, platform, options.features)


def _refuse_unresolved(version_meta: VersionMeta, arguments: tuple[str, ...]) -> None:
    """Một biến còn sót là lệnh sai. Thà không chạy còn hơn chạy rồi hỏng khó hiểu."""
    leftover = unresolved_placeholders(arguments)
    if leftover:
        message = (
            f"{version_meta.version_id}: còn biến chưa thay trong lệnh khởi động: "
            f"{', '.join(sorted(set(leftover)))}"
        )
        raise VersionError(message)


def _secret_values(player_profile: PlayerProfile) -> frozenset[str]:
    """Chỉ che vé thật. Che cả vé giả `"0"` sẽ che nhầm mọi tham số có giá trị 0."""
    access_token = player_profile.access_token
    return frozenset({access_token}) if len(access_token) > 4 else frozenset()
