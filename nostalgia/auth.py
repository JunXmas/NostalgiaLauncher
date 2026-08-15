"""Đăng nhập Microsoft -> Xbox Live -> XSTS -> Minecraft Services.

Dùng device code flow: phù hợp app desktop, không cần nhúng trình duyệt
và không cần client secret.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests

# Đăng ký app tại https://portal.azure.com (Azure Active Directory > App registrations).
# Chọn "Personal Microsoft accounts only" và bật "Allow public client flows".
# Sau đó đặt biến môi trường MC_CLIENT_ID.
DEVICE_CODE_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
SCOPE = "XboxLive.signin offline_access"

XBL_URL = "https://user.auth.xboxlive.com/user/authenticate"
XSTS_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
MC_LOGIN_URL = "https://api.minecraftservices.com/authentication/login_with_xbox"
MC_PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"

TIMEOUT = 30


class AuthError(Exception):
    pass


@dataclass
class MinecraftSession:
    """Kết quả của một lần đăng nhập thành công."""

    access_token: str
    refresh_token: str
    # owns=False nghĩa là tài khoản hợp lệ nhưng chưa mua game -> chạy demo.
    owns_game: bool
    # Chỉ có khi owns_game=True; tài khoản demo chưa có profile Minecraft.
    uuid: str | None = None
    username: str | None = None
    skin_url: str = ""


def _active_skin(profile: dict) -> str:
    for skin in profile.get("skins", []):
        if skin.get("state") == "ACTIVE":
            return skin.get("url", "")
    return ""


def request_device_code(client_id: str) -> dict:
    r = requests.post(
        DEVICE_CODE_URL,
        data={"client_id": client_id, "scope": SCOPE},
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        raise AuthError(_explain_aad(r))
    return r.json()


# Vài mã lỗi AAD hay gặp lúc mới dựng app; thông báo gốc của Microsoft nói bằng
# thuật ngữ nội bộ nên dịch sang việc cần làm.
_AAD_HINTS = {
    "AADSTS70002": (
        "Your Azure application has not enabled 'Allow public client flows'.\n\n"
        "Go to portal.azure.com > App registrations > your app > Authentication "
        "> Advanced settings > Allow public client flows: Yes > Save."
    ),
    "AADSTS700016": (
        "No application found with this client ID in the consumers tenant.\n\n"
        "Double-check the Application (client) ID, and Supported account types must be "
        "'Personal accounts only'."
    ),
    "AADSTS50194": (
        "The application is single-tenant so it cannot use the consumers endpoint. "
        "Change Supported account types to 'Personal accounts only'."
    ),
}


def _explain_aad(response) -> str:
    try:
        data = response.json()
    except ValueError:
        return f"Microsoft returned HTTP {response.status_code}."
    description = data.get("error_description", "")
    for code, hint in _AAD_HINTS.items():
        if code in description:
            return hint
    return f"Microsoft refused ({data.get('error', response.status_code)}): {description[:300]}"


def poll_for_token(client_id: str, device_code: str, interval: int, expires_in: int) -> dict:
    """Chờ người dùng nhập mã trên microsoft.com/link."""
    deadline = time.monotonic() + expires_in
    while time.monotonic() < deadline:
        time.sleep(interval)
        r = requests.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()
        error = r.json().get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        raise AuthError(f"Microsoft sign-in failed: {r.json().get('error_description', error)}")
    raise AuthError("Timed out waiting for the code.")


def refresh_microsoft_token(client_id: str, refresh_token: str) -> dict:
    r = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": SCOPE,
        },
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        raise AuthError("Refresh token expired — please sign in again.")
    return r.json()


def _xbox_live(ms_access_token: str) -> tuple[str, str]:
    r = requests.post(
        XBL_URL,
        json={
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": f"d={ms_access_token}",
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT",
        },
        headers={"Accept": "application/json"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    return data["Token"], data["DisplayClaims"]["xui"][0]["uhs"]


def _xsts(xbl_token: str) -> str:
    r = requests.post(
        XSTS_URL,
        json={
            "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl_token]},
            "RelyingParty": "rp://api.minecraftservices.com/",
            "TokenType": "JWT",
        },
        headers={"Accept": "application/json"},
        timeout=TIMEOUT,
    )
    if r.status_code == 401:
        xerr = str(r.json().get("XErr", ""))
        messages = {
            "2148916233": "This Microsoft account has no Xbox profile. Create one at xbox.com first.",
            "2148916235": "Xbox Live is not available in this account's country.",
            "2148916238": "Child account: it must be added to a Family group.",
        }
        raise AuthError(messages.get(xerr, f"XSTS refused (XErr={xerr})."))
    r.raise_for_status()
    return r.json()["Token"]


def _minecraft_login(xsts_token: str, uhs: str) -> str:
    r = requests.post(
        MC_LOGIN_URL,
        json={"identityToken": f"XBL3.0 x={uhs};{xsts_token}"},
        timeout=TIMEOUT,
    )
    if r.status_code == 403:
        # Azure app tạo sau đợt siết của Microsoft phải được duyệt mới gọi được
        # Minecraft Services. Chưa duyệt thì đúng bước này trả 403, không phải
        # lỗi mã nguồn hay sai token.
        raise AuthError(
            "Minecraft Services refused (403): your Azure application has not been "
            "granted access to the Minecraft API.\n\n"
            "Submit the review form at https://aka.ms/mce-reviewappid and wait for "
            "Microsoft (after approval it can take up to 24 hours to take effect)."
        )
    r.raise_for_status()
    return r.json()["access_token"]


def fetch_profile(mc_access_token: str) -> dict | None:
    """Trả về profile, hoặc None nếu tài khoản chưa mua game."""
    r = requests.get(
        MC_PROFILE_URL,
        headers={"Authorization": f"Bearer {mc_access_token}"},
        timeout=TIMEOUT,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def complete_login(ms_token_response: dict) -> MinecraftSession:
    """Đổi token Microsoft lấy phiên Minecraft, tự phát hiện có bản quyền hay không."""
    xbl_token, uhs = _xbox_live(ms_token_response["access_token"])
    xsts_token = _xsts(xbl_token)
    mc_token = _minecraft_login(xsts_token, uhs)

    profile = fetch_profile(mc_token)
    if profile is None:
        # Tài khoản hợp lệ nhưng chưa mua -> demo mode.
        return MinecraftSession(
            access_token=mc_token,
            refresh_token=ms_token_response["refresh_token"],
            owns_game=False,
        )
    return MinecraftSession(
        access_token=mc_token,
        refresh_token=ms_token_response["refresh_token"],
        owns_game=True,
        uuid=profile["id"],
        username=profile["name"],
        skin_url=_active_skin(profile),
    )
