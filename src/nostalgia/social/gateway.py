"""HTTPS và OAuth trình duyệt; không nhận mật khẩu Google ở launcher."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import asdict
from urllib.parse import urlsplit

from nostalgia.errors import SessionRevoked, SocialError
from nostalgia.model.json_value import JsonValue, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json
from nostalgia.social.envelope import InvitationCipher
from nostalgia.social.model import FriendMessage, GoogleLogin, SocialSnapshot
from nostalgia.social.parse import identifier, parse_messages, parse_snapshot, timestamp
from nostalgia.social.profile_model import ProfileDraft, SocialProfile
from nostalgia.social.profile_parse import parse_profile


class HttpSocialGateway:
    def __init__(self, base_url: str, http_client: HttpClient) -> None:
        parts = urlsplit(base_url)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or parts.path not in ("", "/")
        ):
            raise SocialError("Cấu hình dịch vụ tài khoản không hợp lệ.")
        self.base_url = base_url.rstrip("/")
        self._http_client = http_client
        self.access_token = ""
        self._cipher: InvitationCipher | None = None
        self._registered_token = ""
        self._account_id = ""

    def start_login(self) -> GoogleLogin:
        verifier = secrets.token_hex(32)
        fields = as_mapping(
            self._request(
                "POST",
                "/v1/auth/google/start",
                {
                    "challenge": hashlib.sha256(verifier.encode()).hexdigest(),
                },
                authenticated=False,
            )
        )
        authorization_url = as_string(fields.get("authorization_url")) or ""
        parts = urlsplit(authorization_url)
        if (
            parts.scheme != "https"
            or parts.netloc != "accounts.google.com"
            or parts.path != "/o/oauth2/v2/auth"
            or parts.fragment
            or len(authorization_url) > 4096
        ):
            raise SocialError("Địa chỉ đăng nhập Google không hợp lệ.")
        return GoogleLogin(
            identifier(as_string(fields.get("login_id")) or ""),
            authorization_url,
            timestamp(fields.get("expires_at")),
            verifier,
        )

    def poll_login(self, login: GoogleLogin) -> str:
        fields = as_mapping(
            self._request(
                "POST",
                "/v1/auth/google/poll",
                {
                    "login_id": login.login_id,
                    "verifier": login.verifier,
                },
                authenticated=False,
            )
        )
        if fields.get("status") == "waiting":
            return ""
        if fields.get("status") == "denied":
            raise SocialError("Bạn đã hủy đăng nhập Google. Hãy thử lại khi sẵn sàng.")
        access_token = as_string(fields.get("access_token")) or ""
        if fields.get("status") != "signed_in" or not re.fullmatch(
            r"[A-Za-z0-9_-]{32,256}", access_token
        ):
            raise SocialError("Phiên đăng nhập Google không hợp lệ.")
        return access_token

    def fetch_snapshot(self) -> SocialSnapshot:
        if self._registered_token != self.access_token:
            self._cipher = InvitationCipher()
            self._request(
                "POST", "/v1/auth/encryption-key", {"public_key": self._cipher.public_key}
            )
            self._registered_token = self.access_token
        snapshot = parse_snapshot(self._request("GET", "/v1/me"))
        self._account_id = snapshot.account.account_id
        return snapshot

    def fetch_messages(self, account_id: str) -> tuple[FriendMessage, ...]:
        return parse_messages(
            self._request("GET", "/v1/friends/" + identifier(account_id) + "/messages")
        )

    def friend_action(self, action: str, account_id: str) -> None:
        if action not in {"request", "accept", "remove", "block"}:
            raise SocialError("Thao tác kết bạn không hợp lệ.")
        if action == "request":
            self._request(
                "POST", "/v1/friends/request", {"friend_code": account_id.strip().upper()}
            )
        else:
            self._request("POST", "/v1/friends/" + identifier(account_id) + "/" + action, {})

    def send_message(self, account_id: str, text: str, message_id: str) -> None:
        self._request(
            "POST",
            "/v1/friends/" + identifier(account_id) + "/messages",
            {"text": text, "message_id": identifier(message_id)},
        )

    def send_invite(
        self, account_id: str, room_code: str, host_ticket: str, world_name: str
    ) -> None:
        target = identifier(account_id)
        fields = as_mapping(self._request("GET", "/v1/friends/" + target + "/key"))
        public_key = as_string(fields.get("public_key")) or ""
        if not self._cipher or not re.fullmatch(r"[0-9a-f]{64}", public_key):
            raise SocialError("Bạn cần mở launcher và đăng nhập trước khi nhận lời mời.")
        self._request(
            "POST",
            "/v1/invitations",
            {
                "target": target,
                "room_id": room_code[:6],
                "host_ticket": host_ticket,
                "world_name": world_name,
                "recipient_key": public_key,
                "envelope": self._cipher.encrypt(room_code, target, public_key),
            },
        )

    def accept_invite(self, invite_id: str) -> str:
        fields = as_mapping(
            self._request("POST", "/v1/invitations/" + identifier(invite_id) + "/accept", {})
        )
        if self._cipher is None:
            raise SocialError("Cần đăng nhập lại để xác minh lời mời.")
        room_code = self._cipher.decrypt(fields, self._account_id)
        if not re.fullmatch(r"[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{18}", room_code):
            raise SocialError("Lời mời phòng không hợp lệ.")
        return room_code

    def decline_invite(self, invite_id: str) -> None:
        self._request("POST", "/v1/invitations/" + identifier(invite_id) + "/decline", {})

    def update_profile(self, accent: str, show_badge: bool) -> None:
        self._request("POST", "/v1/profile", {"accent": accent, "show_badge": show_badge})

    def fetch_profile(self, account_id: str) -> SocialProfile:
        return parse_profile(self._request("GET", "/v1/profiles/" + identifier(account_id)))

    def save_profile(self, draft: ProfileDraft) -> SocialProfile:
        return parse_profile(self._request("POST", "/v1/profiles/me", asdict(draft)))

    def fetch_preview_url(self, target: str) -> str:
        fields = as_mapping(self._request("POST", "/v1/plus/preview", {"target": target}))
        value = as_string(fields.get("url")) or ""
        parts = urlsplit(value)
        if (
            parts.scheme != "https"
            or parts.netloc != urlsplit(self.base_url).netloc
            or parts.path != "/v1/plus/preview/download"
            or parts.fragment
        ):
            raise SocialError("Địa chỉ bản thử nghiệm không hợp lệ.")
        return value

    def logout(self) -> None:
        self._request("POST", "/v1/auth/logout", {})

    def _request(
        self, method: str, path: str, document: JsonValue = None, *, authenticated: bool = True
    ) -> JsonValue:
        headers = {"Accept": "application/json"}
        if authenticated:
            if not self.access_token:
                raise SessionRevoked("Cần đăng nhập Google để dùng bạn bè và Plus.")
            headers["Authorization"] = "Bearer " + self.access_token
        payload = json.dumps(document).encode() if document is not None else None
        if payload is not None:
            headers["Content-Type"] = "application/json"
        response = self._http_client.send(
            method,
            self.base_url + path,
            headers=headers,
            body=payload,
            max_bytes=512_000 if path == "/v1/me" else 256_000,
        )
        if response.status == 401 and authenticated:
            raise SessionRevoked(
                "Phiên đã hết hạn hoặc tài khoản vừa đăng nhập trên máy khác. Hãy đăng nhập lại."
            )
        if not response.is_ok:
            messages = {
                403: "Không có quyền với tài khoản này.",
                404: "Không tìm thấy bạn hoặc lời mời đã hết hạn.",
                409: "Phòng không còn mở hoặc thao tác đã được thực hiện.",
                429: "Bạn thao tác quá nhanh. Hãy thử lại sau.",
                503: "Dịch vụ chưa sẵn sàng. Hãy thử lại sau.",
            }
            raise SocialError(
                messages.get(response.status, "Không xác nhận được với dịch vụ tài khoản.")
            )
        return decode_json(response.body, what="dịch vụ tài khoản")
