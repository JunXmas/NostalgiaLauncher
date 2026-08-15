"""Danh tính ở tầng launcher, tách rời khỏi mọi UUID của Minecraft.

Vì sao cần một ID riêng: UUID của hồ sơ offline sinh từ tên người chơi, còn UUID
premium do Mojang cấp — hai giá trị hoàn toàn khác nhau. Bất cứ thứ gì gắn theo
UUID Minecraft đều đứt gãy đúng lúc người chơi chuyển từ offline sang premium.
Một ID sinh cục bộ, không suy ra từ UUID nào, thì sống sót qua chuyển đổi đó.

Liên kết với nhà cung cấp bên ngoài (Google) chỉ là một *khoá ngoài* gắn thêm vào
danh tính, để sau này khôi phục được cùng danh tính trên máy khác.
"""

from __future__ import annotations

import json
import os
import uuid as uuidlib
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .paths import CONFIG_DIR

STORE_PATH = CONFIG_DIR / "identity.json"


@dataclass
class ExternalLink:
    """Khoá ngoài trỏ tới danh tính này ở một nhà cung cấp OAuth."""

    provider: str          # "google"
    subject: str           # claim `sub` — định danh ổn định, không đổi khi đổi email
    email: str = ""
    display_name: str = ""


@dataclass
class PlayerIdentity:
    """Một người chơi, có thể sở hữu nhiều tài khoản Minecraft."""

    player_id: str
    display_name: str = ""
    links: list[ExternalLink] = field(default_factory=list)
    # Nhãn của các tài khoản trong AccountStore thuộc về danh tính này.
    account_labels: list[str] = field(default_factory=list)

    @classmethod
    def create(cls, display_name: str = "") -> PlayerIdentity:
        # uuid4 thuần: cố tình KHÔNG suy ra từ tên hay UUID Minecraft, để đổi tên
        # hay lên premium cũng không làm đổi ID.
        return cls(player_id=str(uuidlib.uuid4()), display_name=display_name)

    def link_for(self, provider: str) -> ExternalLink | None:
        return next((l for l in self.links if l.provider == provider), None)

    @property
    def is_linked(self) -> bool:
        return bool(self.links)


class IdentityStore:
    def __init__(self, path: Path | None = None):
        self.path = path or STORE_PATH
        self.identities: list[PlayerIdentity] = []
        self.active_id: str | None = None
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text())
        self.identities = [
            PlayerIdentity(
                player_id=i["player_id"],
                display_name=i.get("display_name", ""),
                links=[ExternalLink(**l) for l in i.get("links", [])],
                account_labels=list(i.get("account_labels", [])),
            )
            for i in raw.get("identities", [])
        ]
        self.active_id = raw.get("active")

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Chứa email và khoá ngoài -> chỉ chủ sở hữu đọc được.
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"active": self.active_id,
                       "identities": [asdict(i) for i in self.identities]}, f, indent=2)

    # ---------- truy vấn ----------

    def get(self, player_id: str | None) -> PlayerIdentity | None:
        wanted = player_id or self.active_id
        return next((i for i in self.identities if i.player_id == wanted), None)

    def by_subject(self, provider: str, subject: str) -> PlayerIdentity | None:
        for identity in self.identities:
            link = identity.link_for(provider)
            if link and link.subject == subject:
                return identity
        return None

    def for_account(self, label: str) -> PlayerIdentity | None:
        return next((i for i in self.identities if label in i.account_labels), None)

    def active(self) -> PlayerIdentity:
        """Luôn có một danh tính; máy mới thì tạo một cái cục bộ chưa liên kết."""
        current = self.get(None)
        if current is None:
            current = PlayerIdentity.create("Người chơi")
            self.identities.append(current)
            self.active_id = current.player_id
            self.save()
        return current

    # ---------- thay đổi ----------

    def attach_account(self, label: str, player_id: str | None = None) -> PlayerIdentity:
        """Gắn một tài khoản Minecraft vào danh tính, gỡ nó khỏi danh tính cũ."""
        target = self.get(player_id) or self.active()
        for identity in self.identities:
            if identity is not target and label in identity.account_labels:
                identity.account_labels.remove(label)
        if label not in target.account_labels:
            target.account_labels.append(label)
        self.save()
        return target

    def detach_account(self, label: str) -> None:
        for identity in self.identities:
            if label in identity.account_labels:
                identity.account_labels.remove(label)
        self.save()

    def link_external(self, provider: str, subject: str, email: str = "",
                      display_name: str = "") -> PlayerIdentity:
        """Gắn khoá ngoài vào danh tính đang dùng.

        Nếu khoá đó đã thuộc một danh tính khác trên máy này thì chuyển sang dùng
        danh tính ấy — cùng một người, không tạo bản sao.
        """
        existing = self.by_subject(provider, subject)
        if existing is not None:
            self.active_id = existing.player_id
            if display_name and not existing.display_name:
                existing.display_name = display_name
            self.save()
            return existing

        identity = self.active()
        identity.links = [l for l in identity.links if l.provider != provider]
        identity.links.append(ExternalLink(provider, subject, email, display_name))
        if display_name:
            identity.display_name = display_name
        self.save()
        return identity

    def unlink_external(self, provider: str) -> None:
        identity = self.active()
        identity.links = [l for l in identity.links if l.provider != provider]
        self.save()
