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
from nostalgia.auth.device_code import DeviceCode
from nostalgia.auth.qr import QrCode
from nostalgia.content.updates import ContentUpdate
from nostalgia.doctor import Diagnosis
from nostalgia.donate.vietqr import BankAccount
from nostalgia.facade.backups import BackupOperations
from nostalgia.facade.content import ContentTarget
from nostalgia.facade.donate import DonateOperations
from nostalgia.facade.importing import ImportOperations
from nostalgia.facade.instances import InstanceOperations
from nostalgia.facade.mod_repair import ModRepairOperations
from nostalgia.facade.multiplayer import MultiplayerOperations
from nostalgia.facade.nos_client import NosClientOperations
from nostalgia.facade.play import PlayOperations
from nostalgia.facade.presets import PresetOperations
from nostalgia.facade.room_sync import RoomSyncOperations
from nostalgia.facade.servers import ServerOperations
from nostalgia.facade.skins import SkinOperations
from nostalgia.facade.updates import SELF_UPDATING_KINDS, StagedUpdate, UpdateOperations
from nostalgia.importing.launchers import Found
from nostalgia.instance.model import Instance
from nostalgia.instance.server_list import RecentServer
from nostalgia.instance.world import RecentWorld
from nostalgia.launch.game_process import GameProcess
from nostalgia.launch.runner import InstallReport
from nostalgia.modcheck.model import ModScan
from nostalgia.modrepair.gateway import HttpRepairGateway
from nostalgia.modrepair.model import RepairGateway, RepairPlan, RepairScan
from nostalgia.multiplayer.lan_output import lan_port_from_output
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.service import RoomService
from nostalgia.multiplayer.sync_gateway import HttpRoomSyncGateway
from nostalgia.multiplayer.sync_model import RoomSyncGateway, SyncManifest, SyncSnapshot
from nostalgia.nos_client.config import NosClientConfig
from nostalgia.operations.progress import Progress
from nostalgia.payment.gateway import HttpPaymentGateway
from nostalgia.payment.model import PaymentCheckout, PaymentGateway, PaymentOffer, PaymentOrder
from nostalgia.server.content_model import (
    InstalledServerContent,
    ServerContentVersion,
    ServerProject,
)
from nostalgia.server.gateway import HttpServerGateway
from nostalgia.server.manager import ServerManager, ServerSelection
from nostalgia.server.model import (
    ENGINES,
    DedicatedServer,
    ServerAccess,
    ServerArtifact,
    ServerConnection,
    ServerGateway,
    ServerLease,
)
from nostalgia.server.properties import ServerProperties
from nostalgia.settings.store import Settings
from nostalgia.skin.model import PlayerSkin
from nostalgia.social.configuration import ServiceConfiguration
from nostalgia.social.gateway import HttpSocialGateway
from nostalgia.social.model import (
    FriendMessage,
    GoogleLogin,
    ServiceSessionStore,
    SocialGateway,
    SocialSnapshot,
    SocialUpdate,
)
from nostalgia.update.release import LauncherRelease


@dataclass(frozen=True, slots=True)
class Launcher(
    ServerOperations,
    ModRepairOperations,
    BackupOperations,
    DonateOperations,
    UpdateOperations,
    MultiplayerOperations,
    RoomSyncOperations,
    SkinOperations,
    PresetOperations,
    NosClientOperations,
    ImportOperations,
    InstanceOperations,
    PlayOperations,
):
    """Toàn bộ khả năng của lõi, gói sau một đối tượng dựng một lần rồi dùng lại.

    Thân của từng nhóm thao tác nằm ở `nostalgia/facade/`, tách theo miền; ở đây chỉ ghép
    lại thành một lớp để giao diện có đúng MỘT thứ để import.
    """


__all__ = [
    "ENGINES",
    "SELF_UPDATING_KINDS",
    "Account",
    "BankAccount",
    "ContentTarget",
    "ContentUpdate",
    "DedicatedServer",
    "DeviceCode",
    "Diagnosis",
    "Found",
    "FriendMessage",
    "GameProcess",
    "GoogleLogin",
    "HttpPaymentGateway",
    "HttpRepairGateway",
    "HttpRoomSyncGateway",
    "HttpServerGateway",
    "HttpSocialGateway",
    "InstallReport",
    "InstalledServerContent",
    "Instance",
    "Launcher",
    "LauncherRelease",
    "ModScan",
    "NosClientConfig",
    "PaymentCheckout",
    "PaymentGateway",
    "PaymentOffer",
    "PaymentOrder",
    "PlayerProfile",
    "PlayerSkin",
    "Progress",
    "QrCode",
    "RecentServer",
    "RecentWorld",
    "RepairGateway",
    "RepairPlan",
    "RepairScan",
    "RoomService",
    "RoomStatus",
    "RoomSyncGateway",
    "ServerAccess",
    "ServerArtifact",
    "ServerConnection",
    "ServerContentVersion",
    "ServerGateway",
    "ServerLease",
    "ServerManager",
    "ServerProject",
    "ServerProperties",
    "ServerSelection",
    "ServiceConfiguration",
    "ServiceSessionStore",
    "Settings",
    "SocialGateway",
    "SocialSnapshot",
    "SocialUpdate",
    "StagedUpdate",
    "SyncManifest",
    "SyncSnapshot",
    "lan_port_from_output",
]
