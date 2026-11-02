"""Bổ sung ứng viên IGD cho ICE, giữ DTLS và dọn lease khi đóng peer."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from nostalgia.net.router_discovery import discover_router
from nostalgia.net.router_http import is_router_address
from nostalgia.net.router_mapping import (
    RouterMapping,
    create_mapping,
    remove_mapping,
    renew_mapping,
)

if TYPE_CHECKING:
    from aiortc import RTCPeerConnection

logger = logging.getLogger(__name__)


class PeerRoute:
    def __init__(self, connection: RTCPeerConnection) -> None:
        self.connection = connection
        self._mappings: list[RouterMapping] = []
        self._renewal: asyncio.Task[None] | None = None
        self._closed = False

    async def prepare(self) -> None:
        from aioice import Candidate
        from aioice.candidate import candidate_foundation, candidate_priority

        sctp = self.connection.sctp
        if sctp is None:
            return
        gatherer = sctp.transport.transport.iceGatherer
        await gatherer.gather()
        candidates = gatherer.getLocalCandidates()
        attempted: set[str] = set()
        try:
            async with asyncio.timeout(4):
                for candidate in candidates:
                    if candidate.type != "host" or not is_router_address(candidate.ip):
                        continue
                    if candidate.ip in attempted or len(attempted) >= 2:
                        continue
                    attempted.add(candidate.ip)
                    router = await discover_router(candidate.ip)
                    if router is None:
                        continue
                    mapping = await create_mapping(router, candidate.port)
                    self._mappings.append(mapping)
                    # aiortc 1.15/aioice 0.10: ứng viên dùng đúng socket UDP đã thu thập,
                    # không mở cổng Minecraft và không thay lớp mã hoá DTLS.
                    gatherer._connection._local_candidates.append(
                        Candidate(
                            foundation=candidate_foundation(
                                "srflx", "udp", mapping.external_address
                            ),
                            component=candidate.component,
                            transport="udp",
                            priority=candidate_priority(candidate.component, "srflx"),
                            host=mapping.external_address,
                            port=mapping.external_port,
                            type="srflx",
                            related_address=candidate.ip,
                            related_port=candidate.port,
                        )
                    )
                    logger.info("UPnP ICE candidate ready")
        except Exception as exc:
            # UPnP là phụ: router lạ, thiết bị LAN trả rác (header quá dài, dòng trạng thái hỏng)
            # hay aioice đổi API nội bộ đều chỉ được tắt UPnP, không được giết cả kết nối P2P.
            logger.info("UPnP unavailable; keeping IPv6/STUN candidates: %s", type(exc).__name__)
        finally:
            if self._mappings:
                self._renewal = asyncio.create_task(self._renew())

    async def _renew(self) -> None:
        try:
            while True:
                await asyncio.sleep(120)
                for mapping in self._mappings:
                    try:
                        await renew_mapping(mapping)
                    except Exception as exc:  # lỗi một lần thì vòng sau thử lại
                        logger.warning("UPnP lease renewal failed: %s", type(exc).__name__)
        except asyncio.CancelledError:
            raise

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._renewal is not None:
            self._renewal.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._renewal
        mappings, self._mappings = self._mappings, []
        for mapping in mappings:
            try:
                await remove_mapping(mapping)
            except Exception:
                logger.warning("UPnP lease cleanup failed; short lease will expire")
