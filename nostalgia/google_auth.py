"""Đăng nhập Google theo OAuth 2.0 Authorization Code + PKCE, redirect về loopback.

Đây là luồng Google khuyến nghị cho "installed app": mở trình duyệt hệ thống, nhận
mã trả về ở http://127.0.0.1:<cổng ngẫu nhiên>. Không nhúng webview (Google chặn),
không cần secret thật sự bí mật vì PKCE mới là thứ chống đánh cắp mã.

Đăng ký tại https://console.cloud.google.com > APIs & Services > Credentials >
OAuth client ID > Desktop app, rồi đặt GOOGLE_CLIENT_ID (và GOOGLE_CLIENT_SECRET
nếu Google cấp).
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
SCOPE = "openid email profile"
TIMEOUT = 30

PAGE = """<!doctype html><meta charset="utf-8">
<title>Nostalgia Launcher</title>
<style>body{{font-family:system-ui,sans-serif;background:#16212f;color:#e8eef6;
display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}
div{{text-align:center}}h1{{font-size:20px;font-weight:600}}p{{color:#93a5b8}}</style>
<div><h1>{title}</h1><p>{body}</p></div>"""


class GoogleAuthError(Exception):
    pass


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


class _CallbackHandler(BaseHTTPRequestHandler):
    result: dict = {}

    def do_GET(self):  # noqa: N802
        query = parse_qs(urlparse(self.path).query)
        _CallbackHandler.result = {k: v[0] for k, v in query.items()}
        ok = "code" in _CallbackHandler.result
        page = PAGE.format(
            title="Linked successfully" if ok else "Linking failed",
            body="You can return to Nostalgia Launcher now." if ok
            else _CallbackHandler.result.get("error", "No code received."),
        )
        body = page.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # tắt log ra stderr
        pass


def login(client_id: str, client_secret: str = "", on_url=None, wait_seconds: int = 300) -> dict:
    """Chạy trọn luồng và trả về {sub, email, name}. Hàm này chặn — gọi ở luồng nền."""
    if not client_id:
        raise GoogleAuthError(
            "GOOGLE_CLIENT_ID is not set.\n\nCreate an OAuth client ID of type Desktop app "
            "at console.cloud.google.com, then export GOOGLE_CLIENT_ID."
        )

    verifier = _b64(secrets.token_bytes(48))
    challenge = _b64(hashlib.sha256(verifier.encode()).digest())
    state = _b64(secrets.token_bytes(16))

    _CallbackHandler.result = {}
    server = HTTPServer(("127.0.0.1", 0), _CallbackHandler)
    server.timeout = 1
    redirect_uri = f"http://127.0.0.1:{server.server_port}/"

    url = AUTH_URL + "?" + urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    })
    if on_url:
        on_url(url)

    try:
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline and not _CallbackHandler.result:
            server.handle_request()
    finally:
        server.server_close()

    result = _CallbackHandler.result
    if not result:
        raise GoogleAuthError("Timed out waiting for browser confirmation.")
    if "error" in result:
        raise GoogleAuthError(f"Google refused: {result['error']}")
    if result.get("state") != state:
        # State không khớp nghĩa là phản hồi không đến từ yêu cầu mình vừa gửi.
        raise GoogleAuthError("State mismatch — aborting for safety.")

    data = {
        "client_id": client_id,
        "code": result["code"],
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    if client_secret:
        data["client_secret"] = client_secret

    r = requests.post(TOKEN_URL, data=data, timeout=TIMEOUT)
    if r.status_code != 200:
        raise GoogleAuthError(f"Token exchange failed: {r.text[:200]}")
    access_token = r.json()["access_token"]

    info = requests.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"},
                        timeout=TIMEOUT)
    info.raise_for_status()
    profile = info.json()
    return {
        "sub": profile["sub"],          # ổn định kể cả khi người dùng đổi email
        "email": profile.get("email", ""),
        "name": profile.get("name", profile.get("email", "")),
    }
