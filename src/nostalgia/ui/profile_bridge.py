"""Hồ sơ bạn bè chạy nền, bỏ kết quả muộn và không tự công khai lịch sử chơi."""

from collections.abc import Callable
from dataclasses import asdict, replace
from typing import Any, cast

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import FavoritePack, Launcher, SocialGateway, SocialProfile
from nostalgia.errors import SessionRevoked, SocialError
from nostalgia.ui.account_bridge import AccountBridge
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.profile_media import cache_skin, publish_skin
from nostalgia.ui.social_bridge import SocialBridge
from nostalgia.ui.worker import WorkerBridge


class ProfileBridge(WorkerBridge):
    changed = Signal()
    loaded = Signal()
    cleared = Signal()
    saved = Signal()
    _arrived = Signal(int, object, str, str)

    def __init__(
        self,
        launcher: Launcher,
        social: SocialBridge,
        gateway: SocialGateway | None,
        accounts: AccountBridge,
        main: LauncherBridge,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._social, self._gateway, self._accounts, self._main = social, gateway, accounts, main
        self._cache_dir = launcher.paths.data_dir / "cache" / "social-skins"
        self._profile: SocialProfile | None = None
        self._skin_file, self._note = "", ""
        self._arrived.connect(self._apply)
        self.failed.connect(self._failure)
        social.sessionChanged.connect(self.close)
        social.changed.connect(self._verify_friend)
        accounts.libraryChanged.connect(self.changed)
        main.instancesChanged.connect(self.changed)

    @Property(dict, notify=changed)
    def details(self) -> dict[str, Any]:
        if not self._profile:
            return {}
        p = self._profile
        return {
            "account_id": p.account_id,
            "name": p.name,
            "online": p.online,
            "avatar_url": p.avatar_url,
            "badge": p.badge,
            "accent": p.accent,
            "skinFile": self._skin_file,
            "mine": p.account_id
            == cast(dict[str, Any], self._social.property("account")).get("accountId"),
            "details": {
                "bio": p.details.bio,
                "avatar_mode": p.details.avatar_mode,
                "slim": p.details.slim,
                "decor": p.details.decor,
                "favorite_packs": [
                    asdict(favorite_pack) for favorite_pack in p.details.favorite_packs
                ],
            },
        }

    @Property(str, notify=changed)
    def note(self) -> str:
        return self._note

    @Property(list, notify=changed)
    def skinOptions(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._accounts.property("skinLibrary"))

    @Property(list, notify=changed)
    def packOptions(self) -> list[dict[str, Any]]:
        return [
            {"title": row["label"], "game_version": row["versionId"]}
            for row in cast(list[dict[str, Any]], self._main.property("instances"))
        ]

    @Slot(str)
    def open(self, account_id: str) -> None:
        if not self._social.signedIn or not self._gateway or self.busy:
            return
        self._profile = None
        self._skin_file, self._note = "", "Đang đọc hồ sơ…"
        self.changed.emit()
        gateway = self._gateway
        self._request(lambda: gateway.fetch_profile(account_id), "load")

    def _request(self, work: Callable[[], SocialProfile], operation: str) -> None:
        generation = self.next_generation()

        def perform() -> None:
            try:
                social_profile = work()
                source = cache_skin(self._cache_dir, social_profile.details.skin_png)
                self._arrived.emit(generation, social_profile, source, operation)
            except SessionRevoked as error:
                self._arrived.emit(generation, None, str(error), "revoked")
            except SocialError as error:
                self._arrived.emit(generation, None, str(error), "error")

        self.run_in_background(perform, "Đang đồng bộ hồ sơ…")

    @Slot(int, object, str, str)
    def _apply(self, generation: int, result: object, source: str, operation: str) -> None:
        if not self.is_current(generation):
            return
        if result is None:
            self._note = source
            if operation == "revoked":
                self.close()
                self._social.refresh()
        else:
            self._profile, self._skin_file = cast(SocialProfile, result), source
            self._note = "Đã lưu hồ sơ." if operation == "save" else ""
            self.loaded.emit()
            if operation == "save":
                self.saved.emit()
                self._social.refresh()
        self.changed.emit()

    @Slot(str, str, str, bool, list, str)
    def save(
        self,
        bio: str,
        avatar_mode: str,
        skin_entry_id: str,
        share_skin: bool,
        packs: list[Any],
        decor: str,
    ) -> None:
        social_profile, gateway = self._profile, self._gateway
        if (
            not social_profile
            or not cast(dict[str, Any], self.property("details")).get("mine")
            or self.busy
            or not gateway
        ):
            return
        candidates = {
            p["title"] + "|" + p["game_version"]: p
            for p in cast(list[dict[str, Any]], self.property("packOptions"))
        }
        candidates.update(
            {
                p.title + "|" + p.game_version: asdict(p)
                for p in social_profile.details.favorite_packs
            }
        )
        favorites = tuple(
            FavoritePack(str(p["title"]), str(p["game_version"]))
            for p in packs
            if isinstance(p, dict) and p["title"] + "|" + p["game_version"] in candidates
        )
        option = next(
            (
                s
                for s in cast(list[dict[str, Any]], self.property("skinOptions"))
                if s["entryId"] == skin_entry_id
            ),
            None,
        )
        draft = replace(
            social_profile.details,
            bio=bio,
            avatar_mode=avatar_mode,
            favorite_packs=favorites,
            decor=decor,
        )

        def save_profile() -> SocialProfile:
            candidate = draft
            if share_skin and option:
                skin_png, avatar_png = publish_skin(option["skinFile"])
                candidate = replace(
                    candidate, skin_png=skin_png, avatar_png=avatar_png, slim=option["slim"]
                )
            elif not share_skin:
                candidate = replace(candidate, skin_png="", avatar_png="", slim=False)
            return gateway.save_profile(candidate)

        self._request(save_profile, "save")

    @Slot(str)
    def _failure(self, message: str) -> None:
        self._note = message
        self.changed.emit()

    @Slot()
    def close(self) -> None:
        self.next_generation()
        self._profile, self._skin_file, self._note = None, "", ""
        self.changed.emit()
        self.cleared.emit()

    @Slot()
    def _verify_friend(self) -> None:
        if self._profile and (
            not self._social.signedIn
            or (
                not cast(dict[str, Any], self.property("details")).get("mine")
                and not any(
                    f["accountId"] == self._profile.account_id
                    for f in cast(list[dict[str, Any]], self._social.property("friends"))
                )
            )
        ):
            self.close()
