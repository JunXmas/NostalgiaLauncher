"""Hai phiên bản mod kiểm hash để kiểm thử đổi bản qua HTTPS cục bộ."""

import hashlib
import json
from typing import Any, cast

from local_https_server import LocalHttpsServer, ServerState
from modrinth_fixture import SODIUM, version_document


def releases(server: LocalHttpsServer, server_state: ServerState, *, broken: bool = False) -> None:
    documents = []
    for version_id, payload in [("old", b"old jar"), ("new", b"new jar")]:
        document = version_document(
            SODIUM, loaders=["fabric"], url=server.url(f"/cdn/{version_id}.jar")
        )
        document.update(id=version_id, version_number=version_id)
        artifact = cast(list[dict[str, Any]], document["files"])[0]
        artifact.update(
            filename=f"sodium-{version_id}.jar",
            size=len(payload),
            hashes={"sha1": hashlib.sha1(payload).hexdigest()},
        )
        server_state.add(
            f"/cdn/{version_id}.jar", b"bad jar" if broken and version_id == "new" else payload
        )
        documents.append(document)
    server_state.add(f"/modrinth/project/{SODIUM}/version", json.dumps(documents).encode())
