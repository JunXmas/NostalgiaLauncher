"""Trừu tượng hoá tài khoản + lưu trữ phiên đăng nhập.

Phần dựng lệnh chạy game (launch.py) chỉ làm việc với LaunchIdentity,
không cần biết tài khoản thuộc loại nào.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid as uuidlib
from dataclasses import dataclass, asdict
from pathlib import Path

from . import auth
from .paths import CONFIG_DIR

STORE_PATH = CONFIG_DIR / "accounts.json"


def offline_uuid(name: str) -> str:
    """UUID offline mà server vanilla tự sinh: UUID v3 của 'OfflinePlayer:<tên>'.

    Chỉ dùng cho singleplayer/demo và server LAN đặt online-mode=false.

    KHÔNG thay bằng uuid4(). Đây là bản sao của UUID.nameUUIDFromBytes() phía Java,
    tức là cùng một cái tên phải luôn ra cùng một UUID. Server offline-mode tự tính
    lại giá trị này từ tên người chơi, và world lưu inventory theo UUID. Một UUID
    ngẫu nhiên sẽ khác giá trị server tính ra, và đổi sau mỗi lần khởi động: mỗi ván
    chơi là một người mới, mất sạch đồ và toạ độ.
    """
    digest = bytearray(hashlib.md5(f"OfflinePlayer:{name}".encode()).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30  # version 3
    digest[8] = (digest[8] & 0x3F) | 0x80  # variant RFC 4122
    return str(uuidlib.UUID(bytes=bytes(digest)))


@dataclass
class LaunchIdentity:
    """Thông tin danh tính mà lệnh khởi động game cần."""

    username: str
    uuid: str
    access_token: str
    user_type: str  # "msa" cho tài khoản Microsoft
    demo: bool  # True -> thêm cờ --demo, game chạy bản dùng thử


MSA = "msa"          # tài khoản Microsoft thật (đã mua hoặc chưa mua game)
OFFLINE = "offline"  # hồ sơ cục bộ, không có token; chỉ mở khi đã có chủ sở hữu game


class OwnershipRequired(RuntimeError):
    """Tạo hồ sơ offline khi chưa có tài khoản Microsoft nào sở hữu game."""


@dataclass
class StoredAccount:
    """Bản ghi lưu trên đĩa. access_token hết hạn ~24h nên luôn refresh khi có mạng."""

    label: str
    refresh_token: str
    access_token: str
    owns_game: bool
    uuid: str | None = None
    username: str | None = None
    # Tên hiển thị khi chạy demo; tài khoản đã mua dùng username thật nên bỏ qua.
    demo_name: str = "Player"
    kind: str = MSA
    skin_url: str = ""  # lấy từ profile, dùng cho trang Skin

    @classmethod
    def from_session(cls, session: auth.MinecraftSession, label: str) -> StoredAccount:
        return cls(
            label=label,
            refresh_token=session.refresh_token,
            access_token=session.access_token,
            owns_game=session.owns_game,
            uuid=session.uuid,
            username=session.username,
            skin_url=session.skin_url,
        )

    @classmethod
    def offline(cls, label: str, name: str) -> StoredAccount:
        """Hồ sơ offline: token giả "0", UUID sinh từ tên."""
        return cls(
            label=label,
            refresh_token="",
            access_token="0",
            owns_game=False,
            uuid=offline_uuid(name),
            username=name,
            demo_name=name,
            kind=OFFLINE,
        )


class AccountStore:
    """Danh sách tài khoản + con trỏ tài khoản mặc định, lưu ở một file JSON."""

    def __init__(self, path: Path | None = None):
        # Giải quyết lúc gọi, không phải lúc định nghĩa hàm: nếu đặt STORE_PATH làm
        # giá trị mặc định thì nó bị chốt cứng, đổi module attribute sau vô tác dụng.
        self.path = path or STORE_PATH
        self.accounts: list[StoredAccount] = []
        self.default_label: str | None = None
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text())
        if isinstance(raw, list):  # định dạng đầu tiên, chưa có default
            raw = {"accounts": raw, "default": None}
        self.accounts = [StoredAccount(**item) for item in raw.get("accounts", [])]
        self.default_label = raw.get("default")

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Refresh token là bí mật dài hạn: chỉ chủ sở hữu đọc được.
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(
                {"default": self.default_label, "accounts": [asdict(a) for a in self.accounts]},
                f,
                indent=2,
            )

    def unique_label(self, base: str) -> str:
        """Tránh trùng label khi thêm nhiều tài khoản demo."""
        existing = {a.label for a in self.accounts}
        if base not in existing:
            return base
        n = 2
        while f"{base}-{n}" in existing:
            n += 1
        return f"{base}-{n}"

    def upsert(self, account: StoredAccount) -> None:
        self.accounts = [a for a in self.accounts if a.label != account.label]
        self.accounts.append(account)
        if self.default_label is None:
            self.default_label = account.label
        self.save()

    def remove(self, label: str) -> bool:
        before = len(self.accounts)
        self.accounts = [a for a in self.accounts if a.label != label]
        if len(self.accounts) == before:
            return False
        if self.default_label == label:
            self.default_label = self.accounts[0].label if self.accounts else None
        self.save()
        return True

    def set_default(self, label: str) -> bool:
        if not any(a.label == label for a in self.accounts):
            return False
        self.default_label = label
        self.save()
        return True

    def get(self, label: str | None) -> StoredAccount | None:
        """Lấy theo label, hoặc tài khoản mặc định nếu không nêu tên."""
        wanted = label or self.default_label
        if wanted is None:
            return self.accounts[0] if self.accounts else None
        return next((a for a in self.accounts if a.label == wanted), None)

    # ---------- xử lý danh tính khởi động ----------

    def add_offline(self, name: str, label: str | None = None) -> StoredAccount:
        """Thêm hồ sơ offline thoải mái, không cần check bản quyền."""
        account = StoredAccount.offline(self.unique_label(label or name), name)
        self.upsert(account)
        return account

    def resolve_identity(self, account: StoredAccount, override_name: str | None = None) -> LaunchIdentity:
        """Quyết định danh tính khởi động, phân rẽ rõ ràng Offline và MSA."""
        
        if account.kind == OFFLINE:
            name = override_name or account.username
            # MỞ KHÓA BẢN QUYỀN: Luôn cấp full game (demo=False) cho tài khoản Offline
            return LaunchIdentity(name, offline_uuid(name), "0", OFFLINE, demo=False)

        if account.owns_game:
            # Tài khoản Microsoft đã mua game
            return LaunchIdentity(account.username, account.uuid, account.access_token, MSA, demo=False)

        # Tài khoản Microsoft hợp lệ nhưng chưa mua game -> demo mode chính thức từ server Mojang.
        name = override_name or account.demo_name
        return LaunchIdentity(name, offline_uuid(name), account.access_token, MSA, demo=True)


def refresh_if_online(store: AccountStore, account: StoredAccount, client_id: str) -> StoredAccount:
    """Làm mới token. Nếu không có mạng thì dùng lại bản cache.

    Token cũ vẫn chạy được singleplayer; chỉ server online mới từ chối.
    """
    if account.kind == OFFLINE:
        return account  # hồ sơ offline không có refresh token để làm mới
    try:
        ms_tokens = auth.refresh_microsoft_token(client_id, account.refresh_token)
        session = auth.complete_login(ms_tokens)
    except Exception as e:  # noqa: BLE001 - mất mạng hay token hỏng đều rơi về cache
        print(f"  [offline] Could not refresh session ({e}); using cached data.")
        return account
    refreshed = StoredAccount.from_session(session, account.label)
    # Giữ nguyên tên hiển thị demo mà người dùng đã đặt cho tài khoản này.
    refreshed.demo_name = account.demo_name
    store.upsert(refreshed)
    return refreshed
