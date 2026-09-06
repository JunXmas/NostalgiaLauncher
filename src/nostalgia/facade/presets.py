"""Bản chơi "đóng gói sẵn": chọn phiên bản, launcher tự cài một modpack nổi tiếng cho đúng bản đó.

Hiện có một gói: **Optimized** = Fabulously Optimized (Modrinth `1KVo5zza`) — Fabric + Sodium
+ các mod tối ưu, chơi vanilla mượt hơn hẳn mà không cấu hình gì.
"""

from __future__ import annotations

from dataclasses import dataclass

from nostalgia.content import modrinth
from nostalgia.errors import ContentError
from nostalgia.facade.modpacks import ModpackOperations
from nostalgia.instance.model import Instance
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress

PRESET_PROJECT_IDS: dict[str, str] = {"optimized": "1KVo5zza"}
PRESET_TITLES: dict[str, str] = {"optimized": "Fabulously Optimized"}


@dataclass(frozen=True, slots=True)
class PresetOperations(ModpackOperations):
    def list_preset_game_versions(self, preset: str) -> tuple[str, ...]:
        """Các phiên bản Minecraft mà gói có bản phát hành. CHẠM MẠNG."""
        project_id = _project_id(preset)
        with self.make_http_client() as http_client:
            versions = self.fetch_versions(http_client, "modrinth", project_id)
        seen: dict[str, None] = {}
        for project_version in versions:
            for game_version in project_version.game_versions:
                seen.setdefault(game_version, None)
        return tuple(seen)

    def install_preset(
        self,
        preset: str,
        instance_id: str,
        display_name: str,
        *,
        game_version: str,
        allowed_hosts: tuple[str, ...] | None = None,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> Instance:
        """Cài gói cho ĐÚNG `game_version`; chưa có bản đó thì báo, không lặng lẽ cài bản khác."""
        project_id = _project_id(preset)
        with self.make_http_client() as http_client:
            projects = modrinth.fetch_projects(
                http_client, (project_id,), "modpack", endpoints=self.endpoints
            )
            versions = self.fetch_versions(http_client, "modrinth", project_id)
        project = next(iter(projects.values()), None)
        if project is None:
            message = f"không tìm thấy gói {PRESET_TITLES[preset]} trên Modrinth"
            raise ContentError(message)
        if not any(game_version in v.game_versions for v in versions):
            message = f"{PRESET_TITLES[preset]} chưa có bản cho Minecraft {game_version}"
            raise ContentError(message)
        return self.install_modpack(
            project,
            instance_id,
            display_name,
            game_version=game_version,
            allowed_hosts=allowed_hosts,
            on_progress=on_progress,
            cancel_token=cancel_token,
        )


def _project_id(preset: str) -> str:
    try:
        return PRESET_PROJECT_IDS[preset]
    except KeyError:
        message = f"không có gói đóng sẵn tên {preset!r}"
        raise ContentError(message) from None
