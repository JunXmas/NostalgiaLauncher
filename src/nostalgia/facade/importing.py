"""Nhập bản chơi từ nguồn bên ngoài: file .mrpack, launcher khác, hoặc Rooms sync.

Ba luồng import chung một đường ra (`create_instance`), nhưng mỗi luồng có cách lấy dữ liệu
khác nhau. Facade này gom chúng lại để giao diện chỉ cần gọi một nơi.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from nostalgia.errors import ContentError
from nostalgia.facade.modpacks import ModpackOperations
from nostalgia.importing.model import Found
from nostalgia.instance.model import Instance
from nostalgia.modloader.model import detect_loader_kind
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import Progress, ProgressFn, ignore_progress
from nostalgia.storage.files import ensure_dir

logger = logging.getLogger(__name__)


class ImportOperations(ModpackOperations):
    """Facade cho các luồng import instance từ nguồn bên ngoài."""

    __slots__ = ()

    def scan_external_launchers(self) -> list[Found]:
        """Dò các launcher khác trên máy. An toàn: không bao giờ ném lỗi."""
        from nostalgia.importing.launchers import find_all

        return find_all()

    def import_from_launcher(
        self,
        found: Found,
        instance_id: str,
        display_name: str = "",
        *,
        game_dir_override: str = "",
        cancel_token: CancelToken | None = None,
        on_progress: ProgressFn = ignore_progress,
    ) -> Instance:
        """Copy game_dir + đăng ký instance cho bản chơi tìm được từ launcher khác.

        Copy mods/, config/, resourcepacks/, shaderpacks/, saves/ (nếu có) từ game_dir nguồn
        sang game_dir đích. Không copy libraries/ hay versions/ — kho chung dùng riêng.
        """
        self.require_instance_id_free(instance_id)
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()

        # Quyết định version_id: nếu found có game_version + loader_kind, tìm bản đã cài.
        version_id = found.game_version or ""
        if found.loader_kind != "vanilla" and found.game_version:
            # Tìm bản loader đã cài khớp nhất.
            candidates = [
                installed_id
                for installed_id in self.list_installed_versions()
                if detect_loader_kind(installed_id) == found.loader_kind
                and installed_id.endswith(found.game_version)
            ]
            if candidates:
                version_id = max(candidates)
            else:
                # Chưa cài loader này — dùng vanilla, người dùng tự cài sau.
                logger.info(
                    "chưa có %s cho %s — dùng vanilla",
                    found.loader_kind,
                    found.game_version,
                )

        if not version_id:
            # Không biết phiên bản — dùng rỗng, người dùng sẽ phải chọn sau.
            message = (
                f"không xác định được phiên bản game từ {found.launcher}/{found.instance_name}"
            )
            raise ContentError(message)

        on_progress(Progress(stage="Đăng ký bản chơi", done=0, total=3))

        instance = self.create_instance(
            Instance(
                instance_id=instance_id,
                version_id=version_id,
                display_name=display_name or found.instance_name,
                game_dir_override=game_dir_override,
            )
        )
        target_game_dir = self.instance_game_dir(instance)

        if cancel_token is not None:
            cancel_token.raise_if_cancelled()

        on_progress(Progress(stage="Sao chép dữ liệu", done=1, total=3))

        # Copy các thư mục quan trọng.
        _copy_game_data(found.game_dir, target_game_dir)

        if cancel_token is not None:
            cancel_token.raise_if_cancelled()

        on_progress(Progress(stage="Hoàn tất", done=3, total=3))
        return instance


# ---------------------------------------------------------------------------

# Thư mục cần sao chép khi import từ launcher khác.
_IMPORT_DIRS = ("mods", "config", "resourcepacks", "shaderpacks", "saves", "options.txt")


def _copy_game_data(source: Path, target: Path) -> None:
    """Sao chép dữ liệu game từ thư mục nguồn sang thư mục đích."""
    for name in _IMPORT_DIRS:
        src = source / name
        dst = target / name
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif src.is_file():
            ensure_dir(dst.parent)
            shutil.copy2(src, dst)
