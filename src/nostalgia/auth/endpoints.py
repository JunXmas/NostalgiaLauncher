"""Địa chỉ và hằng của luồng đăng nhập, gom một chỗ.

Đăng nhập Minecraft đi qua **bốn máy chủ khác nhau** của hai công ty: Microsoft phát vé,
Xbox Live đổi vé, XSTS cấp quyền, rồi Minecraft Services mới cho vé chơi game. Rải bốn địa
chỉ đó khắp nơi là cách chắc chắn để một ngày sửa một chỗ mà quên ba chỗ còn lại.

**Mã ứng dụng Azure nằm ngay trong mã nguồn, và điều đó là đúng chuẩn.** Luồng device-code
dùng *public client*: theo thiết kế của OAuth, loại này **không có client secret**, và mã ứng
dụng đi kèm mọi request mà bất cứ người dùng nào cũng bắt được. Nó là **định danh ứng dụng**,
không phải bí mật — giấu nó không bảo vệ được gì, còn bắt mỗi người tự đăng ký một app thì
họ phải chờ Microsoft duyệt tới 24 giờ trước khi đăng nhập được lần đầu. Các trình khởi động
mã nguồn mở khác (PrismLauncher, MultiMC) cũng nhúng thẳng như vậy.

Cái KHÔNG bao giờ được nhúng là client secret và vé đăng nhập của người dùng; ở đây không có
cái nào trong hai thứ đó.
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
# Ely.by: máy chủ Yggdrasil cho tài khoản non-premium, và API root cho authlib-injector.
ELY_AUTH_URL = "https://authserver.ely.by/auth"
ELY_AUTHLIB_ROOT_URL = "https://authserver.ely.by/api/authlib-injector"
AUTHLIB_INJECTOR_LATEST_URL = "https://authlib-injector.yushi.moe/artifact/latest.json"

# App Azure "Nostalgia Launcher" — Personal Microsoft accounts, đã được Microsoft duyệt cho
# gọi Minecraft API. Kế thừa từ chính dự án này ở kho tiền nhiệm.
DEFAULT_CLIENT_ID = "868f1ec1-fa81-46de-a1f3-599156f2edd7"

# Chỉ dành cho ai fork và muốn dùng app Azure của riêng họ.
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
    ely_auth_url: str = ELY_AUTH_URL
    ely_authlib_root_url: str = ELY_AUTHLIB_ROOT_URL
    authlib_injector_latest_url: str = AUTHLIB_INJECTOR_LATEST_URL


DEFAULT_AUTH_ENDPOINTS = AuthEndpoints()
