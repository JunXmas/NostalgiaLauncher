"""Cape Mojang (tài khoản Microsoft): liệt kê cái sở hữu, mặc một cái, gỡ ra.

Cape KHÔNG upload được — Mojang phát theo sự kiện (Migrator, Vanilla...) hoặc bán kèm;
launcher chỉ chọn trong số người chơi đã có. Ba thao tác, đúng như trang minecraft.net:

    GET    /minecraft/profile              → ``capes: [{id, alias, url, state}]``
    PUT    /minecraft/profile/capes/active {"capeId": ...} → mặc
    DELETE /minecraft/profile/capes/active                 → gỡ (không mặc cái nào)

Cả ba cần Bearer token của vé Minecraft — cùng vé với upload skin.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from nostalgia.errors import AccountError, NetworkError
from nostalgia.model.json_value import as_list, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json
from nostalgia.operations.cancellation import CancelToken
from nostalgia.repo.endpoints import DEFAULT_ENDPOINTS, Endpoints

logger = logging.getLogger(__name__)

JSON_CONTENT_TYPE = "application/json"


@dataclass(frozen=True, slots=True)
class OwnedCape:
    """Một cape người chơi sở hữu. ``active`` = đang mặc trong game."""

    cape_id: str
    alias: str  # tên hiển thị Mojang đặt ("Migrator", "Vanilla"...)
    texture_url: str  # ảnh texture để launcher vẽ xem trước
    active: bool


def list_owned_capes(
    http_client: HttpClient,
    access_token: str,
    *,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> tuple[OwnedCape, ...]:
    """CHẠM MẠNG. Đọc hồ sơ Mojang, trả danh sách cape sở hữu (có thể rỗng — đa số rỗng)."""
    try:
        response = http_client.send(
            "GET",
            endpoints.profile_with_capes,
            headers={"Authorization": f"Bearer {access_token}", "Accept": JSON_CONTENT_TYPE},
            cancel_token=cancel_token,
        )
    except NetworkError as exc:
        raise AccountError(f"không đọc được danh sách cape: {exc}") from exc
    if not response.is_ok:
        detail = response.body[:200].decode(errors="replace")
        raise AccountError(f"Mojang từ chối đọc hồ sơ (HTTP {response.status}): {detail}")
    document = as_mapping(decode_json(response.body, what="hồ sơ người chơi"))
    capes = []
    for raw_cape in as_list(document.get("capes")):
        fields = as_mapping(raw_cape)
        cape_id = as_string(fields.get("id"))
        if not cape_id:
            logger.debug("bỏ qua một mục cape thiếu id trong hồ sơ Mojang")
            continue
        capes.append(
            OwnedCape(
                cape_id=cape_id,
                alias=as_string(fields.get("alias")) or "",
                texture_url=as_string(fields.get("url")) or "",
                active=(as_string(fields.get("state")) or "").upper() == "ACTIVE",
            )
        )
    return tuple(capes)


def set_active_cape(
    http_client: HttpClient,
    access_token: str,
    cape_id: str,
    *,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> None:
    """CHẠM MẠNG. Mặc một cape theo id; ``cape_id`` rỗng thì GỠ cape (DELETE)."""
    method = "PUT" if cape_id else "DELETE"
    request_body = json.dumps({"capeId": cape_id}).encode() if cape_id else None
    try:
        response = http_client.send(
            method,
            endpoints.cape_active,
            body=request_body,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": JSON_CONTENT_TYPE},
            cancel_token=cancel_token,
        )
    except NetworkError as exc:
        raise AccountError(f"không đổi được cape: {exc}") from exc
    if not response.is_ok:
        detail = response.body[:200].decode(errors="replace")
        raise AccountError(f"Mojang từ chối đổi cape (HTTP {response.status}): {detail}")
    logger.info("đã %s cape %s", "mặc" if cape_id else "gỡ", cape_id or "(none)")
