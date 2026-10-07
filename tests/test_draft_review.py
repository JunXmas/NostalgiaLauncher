"""Owner draft adapters never issue a production entitlement or take real payments."""

import json
import time
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
from nostalgia_draft.payment import ReviewPayment
from nostalgia_draft.repair import ReviewRepair
from nostalgia_draft.server import ReviewServer
from nostalgia_draft.social import ReviewSocial
from nostalgia_draft.sync import ReviewSync

from mod_fixture import write_fabric
from nostalgia.api import Instance, Launcher
from nostalgia.errors import ContentError, MultiplayerError, ServerError, SocialError
from nostalgia.launch.runner import InstallReport
from nostalgia.modcheck.archive import scan_archives
from nostalgia.modcheck.scan import build_scan
from nostalgia.modrepair.transaction import apply_plan, undo_repair
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.social.profile_model import FavoritePack, ProfileDraft
from nostalgia.version.meta import VersionMeta


def test_draft_profile_persists_one_cosmetic_without_touching_real_accounts(tmp_path: Path) -> None:
    account_file = tmp_path / "accounts.json"
    account_file.write_bytes(b"real credentials stay unchanged")
    gateway = ReviewSocial(tmp_path / "draft-review")
    profile_draft = ProfileDraft(decor="amber", favorite_packs=(FavoritePack("Pack", "1.20.1"),))
    gateway.save_profile(profile_draft)
    assert ReviewSocial(tmp_path / "draft-review").profile_draft == profile_draft
    assert account_file.read_bytes() == b"real credentials stay unchanged"
    with pytest.raises(SocialError):
        gateway.start_login()
    with pytest.raises(SocialError):
        gateway.send_invite("friend", "room", "ticket", "world")


def test_review_tier_gates_and_lease_renewal(tmp_path: Path) -> None:
    social = ReviewSocial(tmp_path)
    gateway = ReviewServer(social)
    assert gateway.authorize().plan_name == "Ultimate"
    lease = gateway.start("local-server")
    renewed = gateway.renew(lease)
    assert renewed.server_id == "local-server"
    with pytest.raises(ServerError):
        gateway.start("another-server")
    gateway.release(renewed)
    social.select_plan("plus-month-v1")
    with pytest.raises(ServerError):
        gateway.authorize()
    social.select_plan("plus-half-year-v1")
    assert gateway.authorize().plan_name == "Pro"
    social.logout()
    with pytest.raises(ServerError):
        gateway.start("local-server")


def test_payment_stays_pending_without_explicit_test_action_and_has_no_bank() -> None:
    gateway = ReviewPayment()
    order = gateway.create_order(gateway.fetch_offer("plus-month-v1"), "request")
    assert order.qr_image.startswith("data:image/png;base64,")
    assert not order.account_number and not order.checkout_url
    assert gateway.fetch_order(order).status == "pending"
    gateway.paid = True
    assert gateway.fetch_order(order).status == "paid"
    gateway.create_order(gateway.fetch_offer("plus-lifetime-v1"), "new-request")
    assert not gateway.paid


def test_review_repair_runs_real_transaction_and_undo_and_rejects_reused_plan(
    tmp_path: Path,
) -> None:
    write_fabric(tmp_path / "mods/a.jar", "alpha")
    write_fabric(tmp_path / "mods/b.jar", "alpha")
    scan = build_scan(scan_archives(tmp_path), "1.20.1", "fabric", "0.16.0", 17)
    gateway = ReviewRepair(ReviewSocial(tmp_path / "profile"))
    plan = gateway.fetch_plan(scan)
    assert not plan.unresolved
    receipt = apply_plan(tmp_path, scan, plan, gateway, HttpClient(), lambda: False)
    assert (tmp_path / "mods/b.jar.disabled").exists()
    with pytest.raises(ContentError):
        gateway.authorize(plan)
    undo_repair(tmp_path, receipt, lambda: False)
    assert (tmp_path / "mods/b.jar").exists()
    expired = replace(gateway.fetch_plan(scan), expires_at=int(time.time()) - 1)
    with pytest.raises(ContentError):
        gateway.authorize(expired)


def test_review_sync_creates_real_new_instance_preserving_source_and_excluding_world(
    tmp_path: Path,
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "launcher")
    source = Instance("own-pack", "fabric-loader-0.16.0-1.20.1", "Host pack")
    launcher.create_instance(source)
    metadata = launcher.paths.version_json(source.version_id)
    metadata.parent.mkdir(parents=True)
    metadata.write_text(
        json.dumps(
            {
                "id": source.version_id,
                "jar": "1.20.1",
                "mainClass": "main",
                "libraries": [{"name": "net.fabricmc:fabric-loader:0.16.0"}],
            }
        )
    )
    game_dir = launcher.instance_game_dir(source)
    write_fabric(game_dir / "mods/a.jar", "alpha")
    (game_dir / "saves").mkdir()
    (game_dir / "saves/world.dat").write_bytes(b"original world")
    gateway = ReviewSync(tmp_path / "transport")
    status = RoomStatus(role="hosting", room_code="DRAFT-LOCAL", host_ticket="test")
    launcher.publish_room_modpack(gateway, status, source.instance_id, cancel_token=CancelToken())
    manifest = gateway.resolve(status.room_code)
    assert manifest is not None
    assert not any(f.relative_path.startswith("saves") for f in manifest.files)
    report = InstallReport(
        VersionMeta("fabric-loader-0.16.0-1.20.1", "main"), tmp_path / "java", 0, 0, 0
    )
    with patch.object(Launcher, "install_loader", return_value=report):
        copied = launcher.sync_room_modpack(
            gateway, status.room_code, manifest, cancel_token=CancelToken()
        )
    assert copied.instance_id != source.instance_id
    assert (launcher.instance_game_dir(copied) / "mods/a.jar").read_bytes() == (
        game_dir / "mods/a.jar"
    ).read_bytes()
    assert (game_dir / "saves/world.dat").read_bytes() == b"original world"
    with pytest.raises(MultiplayerError):
        gateway.download("wrong-room", manifest.files[0])
