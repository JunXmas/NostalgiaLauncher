"""Mô-đun khách (guest) cho tính năng đồng bộ Rooms."""

from __future__ import annotations

import asyncio
import json
import logging
import dataclasses
from dataclasses import dataclass
from pathlib import Path

from nostalgia.multiplayer.room_manifest import (
    Manifest, ManifestDiff, build_manifest, diff_manifest, manifest_from_dict, safe_paths_only
)
from nostalgia.multiplayer.room_code import split_room_code
from nostalgia.storage.files import resolve_within, sha1_of_file, ensure_dir
from nostalgia.operations.progress import ProgressFn, Progress, ignore_progress
from nostalgia.operations.cancellation import CancelToken
from nostalgia.errors import MultiplayerError, IntegrityError, Cancelled
from nostalgia.net.websocket import TlsContext, WebSocketClient

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30.0

@dataclass(frozen=True, slots=True)
class RoomInfo:
    """Thông tin phòng nhận từ host."""
    host_name: str
    game_version: str
    loader_kind: str
    file_count: int
    total_size: int

async def probe_room(
    relay_url: str,
    room_code: str,
    *,
    tls_context: TlsContext | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> RoomInfo:
    """Kết nối thử relay để lấy thông tin phòng (manifest). Trả RoomInfo.
    
    Nối relay, gửi yêu cầu manifest, nhận manifest JSON, đóng kết nối.
    Dùng nostalgia.multiplayer.room_code.split_room_code để tách room_id, room_secret.
    Ném MultiplayerError nếu thất bại.
    """
    try:
        room_id, room_secret = split_room_code(room_code)
    except ValueError as e:
        raise MultiplayerError("Invalid room code format") from e

    url = f"{relay_url.rstrip('/')}/s/{room_id}?role=guest"

    try:
        async with asyncio.timeout(timeout):
            socket = await WebSocketClient.connect(url, tls_context=tls_context)
            try:
                # Gửi yêu cầu manifest
                req = {"type": "manifest_request", "room_secret": room_secret}
                await socket.send(json.dumps(req).encode("utf-8"))

                # Nhận manifest JSON
                raw_msg = await socket.receive()
                if not raw_msg:
                    raise MultiplayerError("Host closed connection before sending manifest")

                response = json.loads(raw_msg.decode("utf-8"))
                if response.get("error"):
                    raise MultiplayerError(f"Host error: {response['error']}")

                manifest_dict = response.get("manifest")
                if not manifest_dict:
                    raise MultiplayerError("Invalid response from host: missing manifest")

                file_entries = manifest_dict.get("entries", [])

                return RoomInfo(
                    host_name=response.get("host_name", "Unknown Host"),
                    game_version=manifest_dict.get("game_version", ""),
                    loader_kind=manifest_dict.get("loader_kind", ""),
                    file_count=len(file_entries),
                    total_size=sum(fe.get("size", 0) for fe in file_entries),
                )
            finally:
                await socket.close()
    except asyncio.TimeoutError as exc:
        raise MultiplayerError("Timeout connecting to room") from exc
    except Exception as exc:
        if isinstance(exc, MultiplayerError):
            raise
        raise MultiplayerError(f"Failed to probe room: {exc}") from exc


async def build_guest_instance(
    relay_url: str,
    room_code: str,
    game_dir: Path,
    *,
    tls_context: TlsContext | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    on_progress: ProgressFn = ignore_progress,
    cancel_token: CancelToken | None = None,
) -> ManifestDiff:
    """Kết nối host, lấy manifest, diff với local, tải file thiếu vào game_dir.
    
    Luồng:
    1. Nối relay, gửi yêu cầu manifest
    2. Nhận manifest JSON từ host
    3. Build local manifest từ game_dir (hoặc manifest rỗng nếu game_dir chưa có gì)
    4. Diff -> danh sách file cần tải
    5. Gửi danh sách file cần cho host
    6. Nhận từng file, ghi vào game_dir (dùng resolve_within)
    7. Xoá file thừa (to_delete)
    8. Trả ManifestDiff
    
    Verify sha1 sau khi tải. Log warning nếu file không có sha1.
    """
    try:
        room_id, room_secret = split_room_code(room_code)
    except ValueError as e:
        raise MultiplayerError("Invalid room code format") from e

    url = f"{relay_url.rstrip('/')}/s/{room_id}?role=guest"
    
    try:
        async with asyncio.timeout(timeout):
            socket = await WebSocketClient.connect(url, tls_context=tls_context)
            try:
                # 1. Nối relay, gửi yêu cầu manifest
                req = {"type": "manifest_request", "room_secret": room_secret}
                await socket.send(json.dumps(req).encode("utf-8"))

                # 2. Nhận manifest JSON từ host
                raw_msg = await socket.receive()
                if not raw_msg:
                    raise MultiplayerError("Host closed connection before sending manifest")

                response = json.loads(raw_msg.decode("utf-8"))
                if response.get("error"):
                    raise MultiplayerError(f"Host error: {response['error']}")

                manifest_dict = response.get("manifest")
                if not manifest_dict:
                    raise MultiplayerError("Invalid response from host: missing manifest")

                host_manifest = manifest_from_dict(manifest_dict)

                # 3. Build local manifest từ game_dir
                if cancel_token:
                    cancel_token.raise_if_cancelled()

                if game_dir.exists():
                    local_manifest = build_manifest(
                        game_dir,
                        host_manifest.game_version,
                        host_manifest.loader_kind,
                    )
                else:
                    local_manifest = Manifest(
                        manifest_version=host_manifest.manifest_version,
                        game_version=host_manifest.game_version,
                        loader_kind=host_manifest.loader_kind,
                        entries=(),
                    )

                # 4. Diff → danh sách file cần tải
                diff = diff_manifest(local_manifest, host_manifest)

                if not diff.to_download and not diff.to_delete:
                    return diff

                # 5. Gửi danh sách file cần cho host
                if diff.to_download:
                    req_files = {
                        "type": "file_request",
                        "files": [fe.relative_path for fe in diff.to_download],
                    }
                    await socket.send(json.dumps(req_files).encode("utf-8"))

                    on_progress(Progress("Downloading files...", 0, len(diff.to_download)))

                    # 6. Nhận từng file, ghi vào game_dir
                    for file_idx, file_task in enumerate(diff.to_download):
                        if cancel_token:
                            cancel_token.raise_if_cancelled()

                        on_progress(
                            Progress(
                                f"Downloading {file_task.relative_path}",
                                file_idx,
                                len(diff.to_download),
                            )
                        )

                        target_path = resolve_within(game_dir, file_task.relative_path)
                        ensure_dir(target_path.parent)

                        total_received = 0
                        with open(target_path, "wb") as out:
                            while total_received < file_task.size:
                                if cancel_token:
                                    cancel_token.raise_if_cancelled()

                                chunk = await socket.receive()
                                if not chunk:
                                    raise MultiplayerError(
                                        f"Connection closed while receiving {file_task.relative_path}"
                                    )

                                out.write(chunk)
                                total_received += len(chunk)

                        # Verify sha1 sau khi tải
                        if file_task.sha1:
                            actual_sha1 = sha1_of_file(target_path)
                            if actual_sha1 != file_task.sha1:
                                raise IntegrityError(
                                    f"SHA1 mismatch for {file_task.relative_path}: "
                                    f"expected {file_task.sha1}, got {actual_sha1}"
                                )
                        else:
                            logger.warning(
                                "File %s has no SHA1 to verify", file_task.relative_path
                            )

                # 7. Xoá file thừa (to_delete)
                for rel_path in diff.to_delete:
                    try:
                        target_path = resolve_within(game_dir, rel_path)
                        if target_path.exists():
                            if target_path.is_file():
                                target_path.unlink(missing_ok=True)
                            elif target_path.is_dir():
                                import shutil

                                shutil.rmtree(target_path)
                    except Exception as exc:
                        logger.warning("Failed to delete %s: %s", rel_path, exc)

                on_progress(Progress("Sync complete", 1, 1))

                # 8. Trả ManifestDiff
                return diff

            finally:
                await socket.close()

    except asyncio.TimeoutError as exc:
        raise MultiplayerError("Timeout syncing room") from exc
    except Exception as exc:
        if isinstance(exc, (MultiplayerError, IntegrityError, Cancelled)):
            raise
        raise MultiplayerError(f"Failed to sync room: {exc}") from exc
