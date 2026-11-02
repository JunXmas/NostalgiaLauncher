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
from nostalgia.content.promotions import Promotion
from nostalgia.content.updates import ContentUpdate
from nostalgia.doctor import Diagnosis
from nostalgia.donate.vietqr import BankAccount
from nostalgia.facade.appearance import AppearanceOperations
from nostalgia.facade.backups import BackupOperations
from nostalgia.facade.content import ContentTarget
from nostalgia.facade.donate import DonateOperations
from nostalgia.facade.importing import ImportOperations
from nostalgia.facade.instances import InstanceOperations, PlayChoices
from nostalgia.facade.local_mod import LocalModOperations
from nostalgia.facade.mod_repair import ModRepairOperations
from nostalgia.facade.multiplayer import MultiplayerOperations
from nostalgia.facade.nos_client import NosClientOperations
from nostalgia.facade.onboarding import OnboardingOperations
from nostalgia.facade.play import PlayOperations
from nostalgia.facade.presets import PresetOperations
from nostalgia.facade.promotions import PromotionOperations
from nostalgia.facade.room_sharing import RoomSharingOperations
from nostalgia.facade.room_sync import RoomSyncOperations
from nostalgia.facade.servers import ServerOperations
from nostalgia.facade.updates import SELF_UPDATING_KINDS, StagedUpdate, UpdateOperations
from nostalgia.importing.launchers import Found
from nostalgia.instance.model import Instance
from nostalgia.instance.server_list import SavedServer
from nostalgia.instance.world import SavedWorld
from nostalgia.launch.game_process import GameProcess
from nostalgia.launch.runner import InstallReport
from nostalgia.modcheck.local_fix import LocalFix, suggest_local_fixes
from nostalgia.modcheck.model import ModScan
from nostalgia.model.local_mod import LocalModImport
from nostalgia.modrepair.gateway import HttpRepairGateway
from nostalgia.modrepair.model import RepairChange, RepairGateway, RepairPlan, RepairScan
from nostalgia.multiplayer.lan_log import LanLogReader
from nostalgia.multiplayer.lan_output import lan_port_from_output
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.service import RoomService
from nostalgia.multiplayer.sync_gateway import HttpRoomSyncGateway
from nostalgia.multiplayer.sync_model import RoomSyncGateway, SyncFile, SyncManifest, SyncSnapshot
from nostalgia.nos_client.config import NosClientConfig
from nostalgia.operations.progress import Progress
from nostalgia.payment.catalog import (
    EARLY_SUPPORTER_BADGE,
    EARLY_SUPPORTER_PLANS,
    OFFERS,
    PLUS_BADGE,
)
from nostalgia.payment.gateway import HttpPaymentGateway
from nostalgia.payment.model import (
    ManualPaymentGateway,
    PaymentCheckout,
    PaymentGateway,
    PaymentOffer,
    PaymentOrder,
)
from nostalgia.server.content_model import (
    InstalledServerContent,
    ServerContentVersion,
    ServerProject,
)
from nostalgia.server.manager import ServerManager, ServerSelection
from nostalgia.server.model import (
    ENGINES,
    DedicatedServer,
    ServerArtifact,
    ServerConnection,
)
from nostalgia.server.properties import ServerProperties
from nostalgia.settings.store import Settings
from nostalgia.skin.model import PlayerSkin
from nostalgia.social.configuration import ServiceConfiguration
from nostalgia.social.cosmetic import can_equip_cosmetic, load_cosmetic_collection
from nostalgia.social.gateway import HttpSocialGateway
from nostalgia.social.model import (
    GoogleLogin,
    ServiceSessionStore,
    SocialGateway,
    SocialSnapshot,
)
from nostalgia.social.profile_model import FavoritePack as FavoritePack
from nostalgia.social.profile_model import ProfileDraft as ProfileDraft
from nostalgia.social.profile_model import SocialProfile as SocialProfile
from nostalgia.update.release import LauncherRelease


@dataclass(frozen=True, slots=True)
class Launcher(
    RoomSharingOperations,
    OnboardingOperations,
    ServerOperations,
    ModRepairOperations,
    BackupOperations,
    DonateOperations,
    UpdateOperations,
    MultiplayerOperations,
    RoomSyncOperations,
    AppearanceOperations,
    LocalModOperations,
    PresetOperations,
    PromotionOperations,
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
    "EARLY_SUPPORTER_BADGE",
    "EARLY_SUPPORTER_PLANS",
    "ENGINES",
    "OFFERS",
    "PLUS_BADGE",
    "SELF_UPDATING_KINDS",
    "Account",
    "BankAccount",
    "ContentTarget",
    "ContentUpdate",
    "DedicatedServer",
    "DeviceCode",
    "Diagnosis",
    "FavoritePack",
    "Found",
    "GameProcess",
    "GoogleLogin",
    "HttpPaymentGateway",
    "HttpRepairGateway",
    "HttpRoomSyncGateway",
    "HttpSocialGateway",
    "InstallReport",
    "InstalledServerContent",
    "Instance",
    "LanLogReader",
    "Launcher",
    "LauncherRelease",
    "LocalFix",
    "LocalModImport",
    "ManualPaymentGateway",
    "ModScan",
    "NosClientConfig",
    "PaymentCheckout",
    "PaymentGateway",
    "PaymentOffer",
    "PaymentOrder",
    "PlayChoices",
    "PlayerProfile",
    "PlayerSkin",
    "ProfileDraft",
    "Progress",
    "Promotion",
    "QrCode",
    "RepairChange",
    "RepairGateway",
    "RepairPlan",
    "RepairScan",
    "RoomService",
    "RoomStatus",
    "RoomSyncGateway",
    "SavedServer",
    "SavedWorld",
    "ServerArtifact",
    "ServerConnection",
    "ServerContentVersion",
    "ServerManager",
    "ServerProject",
    "ServerProperties",
    "ServerSelection",
    "ServiceConfiguration",
    "ServiceSessionStore",
    "Settings",
    "SocialGateway",
    "SocialProfile",
    "SocialSnapshot",
    "StagedUpdate",
    "SyncFile",
    "SyncManifest",
    "SyncSnapshot",
    "can_equip_cosmetic",
    "lan_port_from_output",
    "load_cosmetic_collection",
    "suggest_local_fixes",
]
