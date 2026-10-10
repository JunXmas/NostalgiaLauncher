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


@pytest.mark.parametrize("relay_only", [False, True])
def test_create_room_uses_p2p_without_extra_setup_or_respects_relay_choice(
    host_popup: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch, relay_only: bool
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
    direct = find_control(root_item, "hostDirectAllowed")
    assert direct.property("checked") and not direct.isVisible()
    if relay_only:
        press(view, find_control(root_item, "hostDirectAllowedOptions"))
        assert direct.isVisible()
        press(view, direct)
        assert not direct.property("checked")
    press(view, find_control(root_item, "hostLaunchButton"))
    wait_until(lambda: not popup.property("visible"))
    assert modes == [not relay_only] and launched == ["a"]
    assert not warnings


@pytest.mark.parametrize("relay_only", [False, True])
def test_accept_invitation_uses_p2p_without_extra_setup_or_respects_relay_choice(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch, relay_only: bool
) -> None:
    _, _, view, root_item, social, multiplayer, sync_bridge, _ = social_preview
    login_preview(social_preview)
    social._timer.stop()
    modes: list[bool] = []
    joined: list[str] = []
    monkeypatch.setattr(multiplayer._service, "set_direct_allowed", modes.append)
    monkeypatch.setattr(sync_bridge, "join", joined.append)
    direct = social_control(root_item, "guestDirectAllowed-invite")
    assert direct.property("checked") and not direct.isVisible()
    if relay_only:
        press(view, social_control(root_item, "guestDirectAllowed-inviteOptions"))
        assert direct.isVisible()
        press(view, direct)
        assert not direct.property("checked")
    press(view, social_control(root_item, "acceptInvite-invite"))
    wait_until(lambda: not social.inviteBusy and bool(joined))
    assert modes == [not relay_only] and joined == ["ABCDEFABCDEFGHJKMN"]
