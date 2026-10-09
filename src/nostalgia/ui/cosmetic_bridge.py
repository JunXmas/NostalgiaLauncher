"""Own cosmetic library; save only decor while preserving all other profile fields."""

from collections.abc import Callable
from dataclasses import asdict, replace
from typing import Any, cast

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import SocialGateway, SocialProfile, can_equip_cosmetic, load_cosmetic_collection
from nostalgia.errors import SessionRevoked
from nostalgia.ui.social_bridge import SocialBridge
from nostalgia.ui.worker import WorkerBridge


class CosmeticBridge(WorkerBridge):
    changed = Signal()
    _arrived = Signal(int, object)
    _revoked = Signal(int, str)

    def __init__(
        self, social: SocialBridge, gateway: SocialGateway | None, parent: QObject
    ) -> None:
        super().__init__(parent)
        self._social, self._gateway = social, gateway
        self._collection = load_cosmetic_collection()
        self._profile: SocialProfile | None = None
        self._pending = False
        self._owner_id = ""
        self._arrived.connect(self._apply)
        self._revoked.connect(self._on_revoked)
        self.busyChanged.connect(self._drain)
        social.sessionChanged.connect(self._session_changed)
        social.changed.connect(self._sync_owner)

    @Property(dict, notify=changed)
    def details(self) -> dict[str, Any]:
        social_profile = self._profile
        return {
            "loaded": social_profile is not None,
            "decor": social_profile.details.decor if social_profile else "none",
            "avatarUrl": social_profile.avatar_url if social_profile else "",
            "ownedCosmetics": list(social_profile.owned_cosmetics) if social_profile else [],
        }

    @Property(list, constant=True)
    def sets(self) -> list[dict[str, Any]]:
        return [asdict(c) for c in self._collection.sets]

    @Property(int, constant=True)
    def revision(self) -> int:
        return self._collection.revision

    @Slot()
    def refresh(self) -> None:
        account = cast(dict[str, Any], self._social.property("account"))
        gateway = self._gateway
        if not gateway or not account.get("accountId"):
            return
        if self.busy:
            self._pending = True
            return
        self._pending = False
        generation = self.next_generation()
        account_id = str(account["accountId"])
        self._request(generation, lambda: gateway.fetch_profile(account_id))

    @Slot(str)
    def equip(self, decor: str) -> None:
        social_profile, gateway = self._profile, self._gateway
        account = cast(dict[str, Any], self._social.property("account"))
        if (
            self.busy
            or not social_profile
            or not gateway
            or social_profile.account_id != account.get("accountId")
            or (
                decor != "none"
                and not account.get("cosmeticPlus")
                and decor not in social_profile.owned_cosmetics
            )
            or not can_equip_cosmetic(self._collection, decor, social_profile.details.decor)
        ):
            return
        generation = self.next_generation()
        account_id = social_profile.account_id

        def save() -> SocialProfile:
            latest = gateway.fetch_profile(account_id)
            if not self.is_current(generation) or latest.account_id != account_id:
                return latest
            if not can_equip_cosmetic(self._collection, decor, latest.details.decor):
                return latest
            return gateway.save_profile(replace(latest.details, decor=decor))

        self._request(generation, save)

    def _request(self, generation: int, work: Callable[[], SocialProfile]) -> None:
        def perform() -> None:
            try:
                self._arrived.emit(generation, work())
            except SessionRevoked as error:
                self._revoked.emit(generation, str(error))

        self.run_in_background(perform, "Đang đồng bộ diện mạo hồ sơ…")

    @Slot(int, str)
    def _on_revoked(self, generation: int, message: str) -> None:
        if self.is_current(generation):
            self.close()
            self.failed.emit(message)
            self._social.refresh()

    @Slot()
    def _session_changed(self) -> None:
        self.close()
        self.refresh()

    @Slot()
    def _sync_owner(self) -> None:
        account = cast(dict[str, Any], self._social.property("account"))
        owner_id = str(account.get("accountId", ""))
        if owner_id != self._owner_id:
            self._owner_id = owner_id
            self.close()
            self.refresh()

    @Slot()
    def _drain(self) -> None:
        if self._pending and not self.busy:
            self.refresh()

    @Slot(int, object)
    def _apply(self, generation: int, result: object) -> None:
        social_profile = cast(SocialProfile, result)
        account = cast(dict[str, Any], self._social.property("account"))
        if self.is_current(generation) and social_profile.account_id == account.get("accountId"):
            self._profile = social_profile
            self.changed.emit()

    @Slot()
    def close(self) -> None:
        self.next_generation()
        self._pending = False
        self._profile = None
        self.changed.emit()
