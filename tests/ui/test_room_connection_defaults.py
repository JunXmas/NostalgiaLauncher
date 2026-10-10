"""P2P mặc định cho cả host và khách, lựa chọn chỉ relay vẫn tới dịch vụ phòng."""

from typing import Any

import pytest
from test_bridges import wait_until
from test_host_popup import host_popup as host_popup
from test_social_ui import find_control as social_control
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def test_create_room_uses_p2p_without_relay_option(
    host_popup: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, view, bridge, root_item, host, warnings = host_popup
    multiplayer = view.rootContext().contextProperty("multiplayerBridge")
    modes: list[bool] = []
    launched: list[str] = []
    monkeypatch.setattr(multiplayer._service, "set_direct_allowed", modes.append)
    monkeypatch.setattr(
        bridge, "play_hosted", lambda instance_id, *_args: launched.append(instance_id)
    )
    host.openSetup()
    popup = find_control(root_item, "hostDialog")
    wait_until(lambda: popup.property("opened"))
    assert "Relay dữ liệu đã tắt" in find_control(popup, "p2pOnlyStatus").property("text")
    press(view, find_control(root_item, "hostLaunchButton"))
    wait_until(lambda: not popup.property("visible"))
    assert modes == [True] and launched == ["a"]
    assert not warnings


def test_accept_invitation_uses_p2p_without_relay_option(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, view, root_item, social, multiplayer, sync_bridge, _ = social_preview
    login_preview(social_preview)
    social._timer.stop()
    modes: list[bool] = []
    joined: list[str] = []
    monkeypatch.setattr(multiplayer._service, "set_direct_allowed", modes.append)
    monkeypatch.setattr(sync_bridge, "join", joined.append)
    assert "Relay dữ liệu đã tắt" in social_control(root_item, "p2pOnlyStatus").property("text")
    press(view, social_control(root_item, "acceptInvite-invite"))
    wait_until(lambda: not social.inviteBusy and bool(joined))
    assert modes == [True] and joined == ["ABCDEFABCDEFGHJKMN"]
