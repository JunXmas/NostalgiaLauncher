"""Create a server transactionally from a pinned official build; metadata commits last."""

from __future__ import annotations

import re
import shutil
import tempfile
import uuid
from pathlib import Path

from nostalgia.errors import ServerError
from nostalgia.model.json_value import as_integer, as_mapping, as_string
from nostalgia.operations.cancellation import CancelToken
from nostalgia.server.context import ServerContext
from nostalgia.server.download import download_jar
from nostalgia.server.model import DedicatedServer, ServerArtifact, server_engine
from nostalgia.server.properties import DEFAULTS, ServerProperties, save_properties
from nostalgia.server.version_order import validate_game_version


class ServerInstall(ServerContext):
    def versions(self, engine_id: str) -> tuple[str, ...]:
        server_engine(engine_id)
        if engine_id == "vanilla":
            return tuple(
                row.version_id
                for row in self._repository.fetch_manifest().released()
                if re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,2}", row.version_id)
            )
        return self._catalog.versions(engine_id)

    def builds(self, engine_id: str, game_version: str) -> tuple[ServerArtifact, ...]:
        server_engine(engine_id)
        validate_game_version(game_version)
        if engine_id != "vanilla":
            return self._catalog.builds(engine_id, game_version)
        fields = as_mapping(self._repository.sync_raw_version(game_version))
        remote_file = as_mapping(as_mapping(fields.get("downloads")).get("server"))
        url = as_string(remote_file.get("url")) or ""
        digest = as_string(remote_file.get("sha1")) or ""
        if not url or not re.fullmatch(r"[a-f0-9]{40}", digest):
            raise ServerError("Mojang không phát hành server cho bản này.")
        return (
            ServerArtifact(
                engine_id,
                game_version,
                game_version,
                url,
                "sha1",
                digest,
                as_integer(remote_file.get("size")),
            ),
        )

    def install(
        self,
        display_name: str,
        engine_id: str,
        game_version: str,
        build_id: str,
        cancel_token: CancelToken | None = None,
    ) -> DedicatedServer:
        with self._lock:
            self.authorize()
            if self.running_id:
                raise ServerError("Dừng server đang chạy trước khi cài server mới.")
            if (
                not display_name.strip()
                or len(display_name.strip()) > 80
                or any(ord(c) < 32 for c in display_name)
            ):
                raise ServerError("Tên server phải dài 1-80 ký tự và nằm trên một dòng.")
            artifact = next(
                (a for a in self.builds(engine_id, game_version) if a.build_id == build_id), None
            )
            if artifact is None:
                raise ServerError("Bản server đã chọn không còn trong danh mục chính thức.")
            server_id = uuid.uuid4().hex
            destination = self._store.directory(server_id)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=destination.parent, prefix=".create-") as staging:
                stage_dir = Path(staging)
                sha256 = download_jar(
                    self._http_client,
                    artifact.url,
                    stage_dir / "server.jar",
                    algorithm=artifact.hash_algorithm,
                    digest=artifact.digest,
                    size=artifact.size,
                    cancel_token=cancel_token,
                )
                save_properties(stage_dir, ServerProperties(tuple(DEFAULTS.items())))
                if cancel_token:
                    cancel_token.raise_if_cancelled()
                self.authorize()  # Recheck after a long download before registering anything.
                stage_dir.rename(destination)
                server = DedicatedServer(
                    server_id, display_name.strip(), engine_id, game_version, build_id, sha256
                )
                try:
                    self._store.save(server)
                except BaseException:
                    shutil.rmtree(destination)
                    raise
            return server
