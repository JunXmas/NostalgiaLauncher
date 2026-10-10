"""Gửi, nhận và từ chối lời mời không bị khóa bởi cập nhật trạng thái."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import ServiceSessionStore, SocialGateway
from nostalgia.ui.invitation_sender import InvitationSender
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge
from nostalgia.ui.room_sync_bridge import RoomSyncBridge
from nostalgia.ui.social_session import SocialSession


class SocialInvitations(SocialSession):
    inviteBusyChanged = Signal()

    def __init__(
        self,
        gateway: SocialGateway | None,
        multiplayer: MultiplayerBridge,
        sync_bridge: RoomSyncBridge,
        parent: QObject | None = None,
        session_store: ServiceSessionStore | None = None,
        plus_enabled: bool = True,
    ) -> None:
        super().__init__(gateway, multiplayer, sync_bridge, parent, session_store, plus_enabled)
        self._invitation_sender = InvitationSender(self)
        self._invitation_sender.busyChanged.connect(self.inviteBusyChanged)
        self._invitation_sender.completed.connect(self._apply_invitation)

    @Property(bool, notify=inviteBusyChanged)
    def inviteBusy(self) -> bool:
        return bool(self._invitation_sender.busy)

    @Slot(str, str, bool)
    def _apply_invitation(self, room_code: str, error: str, revoked: bool) -> None:
        if revoked:
            if self._session_store:
                self._session_store.remove_access_token()
            self._reset_session(error)
        elif error:
            self._note = error
        elif room_code:
            if not self._multiplayer.active and self._sync_bridge.hostReady:
                self._sync_bridge.join(room_code)
                self._note = "Đã gửi."
            else:
                self._note = "Rời phòng hiện tại để nhận lời mời này."
            self.refresh()
        else:
            self._note = "Đã gửi."
            self.refresh()
        self.changed.emit()

    @Slot(str)
    def inviteFriend(self, account_id: str) -> None:
        gateway, status = self._gateway, self._multiplayer.room_snapshot()
        if (
            self.signedIn
            and gateway
            and not self.inviteBusy
            and status.role in ("hosting", "waiting_world")
            and not status.locked
            and status.room_code
            and status.host_ticket
            and self._sync_bridge.hostReady
            and self._snapshot
            and any(friend.account_id == account_id for friend in self._snapshot.friends)
        ):

            def send() -> str:
                gateway.send_invite(
                    account_id, status.room_code, status.host_ticket, status.world_name
                )
                return ""

            self._invitation_sender.submit(gateway, send)

    @Slot(str)
    def acceptInvite(self, invite_id: str) -> None:
        gateway = self._gateway
        if (
            self.signedIn
            and gateway
            and not self.inviteBusy
            and not self._multiplayer.active
            and self._sync_bridge.hostReady
            and self._snapshot
            and any(invite.invite_id == invite_id for invite in self._snapshot.invitations)
        ):
            self._invitation_sender.submit(gateway, lambda: gateway.accept_invite(invite_id))

    @Slot(str)
    def declineInvite(self, invite_id: str) -> None:
        gateway = self._gateway
        if self.signedIn and gateway and invite_id and not self.inviteBusy:

            def decline() -> str:
                gateway.decline_invite(invite_id)
                return ""

            self._invitation_sender.submit(gateway, decline)

    @Slot()
    def shutdown(self) -> None:
        self._invitation_sender.cancel()
        super().shutdown()

    def _reset_session(self, note: str) -> None:
        self._invitation_sender.cancel()
        super()._reset_session(note)
