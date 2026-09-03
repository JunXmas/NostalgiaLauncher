"""Cây lỗi của mccore.

Mọi lỗi do mccore chủ động phát ra đều kế thừa `McCoreError`, để người gọi bắt được đúng
lỗi của launcher mà không nuốt nhầm lỗi lập trình. Không `raise Exception` trần, không
`except: pass`.

Cây này chỉ chứa lỗi đã có nơi phát ra. Bước nào cần lỗi mới thì thêm ở đúng bước đó —
khai sẵn một cây lỗi đầy đủ mà chưa ai ném là code thừa.
"""

from __future__ import annotations


class McCoreError(Exception):
    """Gốc của mọi lỗi do mccore phát ra."""


class UnsafePathError(McCoreError):
    """Đường dẫn tương đối tìm cách thoát ra ngoài thư mục đích.

    Phát ra khi giải nén archive tải từ mạng (zip-slip) hoặc khi ghép đường dẫn lấy từ dữ
    liệu bên ngoài. Đây là lỗi bảo mật, không phải lỗi dữ liệu — đừng bắt rồi bỏ qua.
    """


class DataFileError(McCoreError):
    """File dữ liệu trên đĩa thiếu, hỏng, hoặc sai cấu trúc."""


class NetworkError(McCoreError):
    """Không lấy được dữ liệu qua mạng: kết nối lỗi, mã trả về lạ, hoặc hết thời gian."""


class IntegrityError(McCoreError):
    """File tải về không khớp kích thước hoặc sha1 mà máy chủ công bố."""


class VersionError(McCoreError):
    """JSON phiên bản sai cấu trúc, thiếu, hoặc kế thừa thành vòng tròn."""


class UnsupportedPlatformError(McCoreError):
    """Hệ điều hành không nằm trong ba hệ mà Mojang phát hành cho."""


class Cancelled(McCoreError):
    """Người dùng yêu cầu dừng giữa chừng."""
