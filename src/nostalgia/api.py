"""Cửa duy nhất mà giao diện được phép đi qua.

Kho tiền nhiệm không có lớp này, và hậu quả đo được: phần giao diện của nó import thẳng vào
**sáu module lõi** (`accounts`, `doctor`, `install`, `launch`, `paths`, `settings`). Mỗi lần
lõi đổi một chi tiết là giao diện gãy theo, và không ai dám sửa lõi nữa.

Luật của lớp này:

- **Nhận và trả dataclass**, không bao giờ trả `dict` thô hay đối tượng của thư viện chuẩn
  như `Popen`. `GameProcess` được trả ra, nhưng nó là bọc có chủ đích: người gọi chỉ thấy
  `pid`, `is_running`, `wait`, `stop`.
- **Dựng một lần, tiêm vào.** `Launcher` giữ `paths` và `platform`; không có đường dẫn mặc
  định ẩn nào nằm rải trong code. Nhờ vậy giao diện mở được hai profile song song, và test
  chạy song song được.
- **Không in ra màn hình.** Tiến độ đi qua `on_progress`, mã đăng nhập đi qua
  `on_device_code` — đúng như tầng `cli/` đang làm.

Giao diện chỉ được import: `nostalgia.api`, `nostalgia.errors`, `nostalgia.operations.progress`
và các dataclass mô hình. Có test gác ở `tests/test_api_boundary.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

from nostalgia.account.model import Account, PlayerProfile
from nostalgia.content.updates import ContentUpdate
from nostalgia.doctor import Diagnosis
from nostalgia.facade.content import ContentTarget
from nostalgia.facade.instances import InstanceOperations
from nostalgia.facade.multiplayer import MultiplayerOperations
from nostalgia.facade.play import PlayOperations
from nostalgia.facade.presets import PresetOperations
from nostalgia.facade.skins import SkinOperations
from nostalgia.instance.model import Instance
from nostalgia.launch.game_process import GameProcess
from nostalgia.launch.runner import InstallReport
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.service import RoomService
from nostalgia.operations.progress import Progress
from nostalgia.settings.store import Settings
from nostalgia.skin.model import PlayerSkin


@dataclass(frozen=True, slots=True)
class Launcher(
    MultiplayerOperations, SkinOperations, PresetOperations, InstanceOperations, PlayOperations
):
    """Toàn bộ khả năng của lõi, gói sau một đối tượng dựng một lần rồi dùng lại.

    Thân của từng nhóm thao tác nằm ở `nostalgia/facade/`, tách theo miền; ở đây chỉ ghép
    lại thành một lớp để giao diện có đúng MỘT thứ để import.
    """


__all__ = [
    "Account",
    "ContentTarget",
    "ContentUpdate",
    "Diagnosis",
    "GameProcess",
    "InstallReport",
    "Instance",
    "Launcher",
    "PlayerProfile",
    "PlayerSkin",
    "Progress",
    "RoomService",
    "RoomStatus",
    "Settings",
]
