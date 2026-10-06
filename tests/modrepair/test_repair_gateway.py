"""HTTPS cục bộ kiểm proof, hash, nguồn tải và đường dẫn từ máy chủ."""

import json
import time
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from mod_fixture import write_fabric
from nostalgia.errors import ContentError
from nostalgia.modcheck.archive import scan_archives
from nostalgia.modcheck.scan import build_scan
from nostalgia.modrepair.gateway import HttpRepairGateway, scan_hash
from nostalgia.net.http import HttpClient


@pytest.mark.parametrize("fault", ["", "path", "origin", "hash", "expired", "unauthorized"])
def test_server_plan_validation(
    tmp_path: Path,
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    fault: str,
) -> None:
    write_fabric(tmp_path / "mods/a.jar", "alpha", depends={"beta": "*"})
    scan = build_scan(scan_archives(tmp_path), "1.20.1", "fabric", "0.16.0", 17)
    change = {
        "operation": "add",
        "file_name": "beta.jar",
        "sha256": "",
        "url": "https://cdn.modrinth.com/data/x/beta.jar",
        "size": 100,
        "sha512": "f" * 128,
        "reason": "Bổ sung",
    }
    fields = {
        "plan_id": "a" * 64,
        "scan_hash": scan_hash(scan),
        "expires_at": int(time.time()) + 900,
        "changes": [change],
        "unresolved": [],
    }
    if fault == "path":
        change["file_name"] = "../beta.jar"
    if fault == "origin":
        change["url"] = "https://cdn.modrinth.com.evil.test/data/beta.jar"
    if fault == "hash":
        fields["scan_hash"] = "b" * 64
    if fault == "expired":
        fields["expires_at"] = 1
    server_state.add(
        "/v1/plus/repair",
        json.dumps(fields).encode(),
        status=403 if fault == "unauthorized" else 200,
    )
    gateway = HttpRepairGateway(server.url(""), "session", http_client)
    if fault:
        with pytest.raises(ContentError):
            gateway.fetch_plan(scan)
    else:
        plan = gateway.fetch_plan(scan)
        assert plan.changes[0].file_name == "beta.jar"
        assert server_state.received_header("/v1/plus/repair", "Authorization") == "Bearer session"
        assert "findings" not in json.loads(server_state.received_body("/v1/plus/repair"))
        endpoint = "/v1/plus/repair/" + plan.plan_id + "/authorize"
        server_state.add(endpoint, b'{"authorized":true}')
        gateway.authorize(plan)
        server_state.add(endpoint, b'{"authorized":false}')
        with pytest.raises(ContentError):
            gateway.authorize(plan)
