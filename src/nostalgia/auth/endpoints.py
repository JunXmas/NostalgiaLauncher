"""Địa chỉ và hằng của luồng đăng nhập, gom một chỗ.

Đăng nhập Minecraft đi qua **bốn máy chủ khác nhau** của hai công ty: Microsoft phát vé,
Xbox Live đổi vé, XSTS cấp quyền, rồi Minecraft Services mới cho vé chơi game. Rải bốn địa
chỉ đó khắp nơi là cách chắc chắn để một ngày sửa một chỗ mà quên ba chỗ còn lại.

**Không có mã ứng dụng nào nằm trong kho này.** Mỗi người phải tự đăng ký app ở
portal.azure.com (App registrations → "Personal Microsoft accounts only" → bật "Allow public
client flows"), rồi xin duyệt truy cập Minecraft API ở https://aka.ms/mce-reviewappid. Mã đó
đưa vào bằng biến môi trường; nhúng cứng mã của người khác là dùng nhờ danh nghĩa của họ.
"""

from __future__ import annotations

from dataclasses import dataclass

# Endpoint `consumers` chứ không phải `common`: tài khoản Minecraft là tài khoản Microsoft
# cá nhân, và app khai "Personal accounts only" sẽ bị `common` từ chối.
DEVICE_CODE_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"

# `offline_access` là thứ đổi lấy refresh token; thiếu nó thì mỗi lần chơi phải đăng nhập lại.
SCOPE = "XboxLive.signin offline_access"
DEVICE_CODE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"

XBOX_LIVE_URL = "https://user.auth.xboxlive.com/user/authenticate"
XSTS_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
MINECRAFT_LOGIN_URL = "https://api.minecraftservices.com/authentication/login_with_xbox"
MINECRAFT_PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"

CLIENT_ID_ENV = "NOSTALGIA_MSA_CLIENT_ID"


@dataclass(frozen=True, slots=True)
class AuthEndpoints:
    """Sáu địa chỉ của bốn máy chủ, gói lại để truyền xuống một lần.

    Truyền sáu tham số URL rời qua từng tầng là cách chắc chắn để một ngày có tầng quên
    chuyển tiếp một cái, và test "offline" lặng lẽ gọi ra Microsoft thật. Đã trả giá đúng
    kiểu đó một lần với địa chỉ object asset.
    """

    device_code_url: str = DEVICE_CODE_URL
    token_url: str = TOKEN_URL
    xbox_live_url: str = XBOX_LIVE_URL
    xsts_url: str = XSTS_URL
    minecraft_login_url: str = MINECRAFT_LOGIN_URL
    minecraft_profile_url: str = MINECRAFT_PROFILE_URL


DEFAULT_AUTH_ENDPOINTS = AuthEndpoints()
