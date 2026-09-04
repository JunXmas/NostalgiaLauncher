"""Cây lỗi của nostalgia.

Mọi lỗi do nostalgia chủ động phát ra đều kế thừa `NostalgiaError`, để người gọi bắt được đúng
lỗi của launcher mà không nuốt nhầm lỗi lập trình. Không `raise Exception` trần, không
`except: pass`.

Cây này chỉ chứa lỗi đã có nơi phát ra. Bước nào cần lỗi mới thì thêm ở đúng bước đó —
khai sẵn một cây lỗi đầy đủ mà chưa ai ném là code thừa.
"""

from __future__ import annotations


class NostalgiaError(Exception):
    """Gốc của mọi lỗi do nostalgia phát ra."""


class UnsafePathError(NostalgiaError):
    """Đường dẫn tương đối tìm cách thoát ra ngoài thư mục đích.

    Phát ra khi giải nén archive tải từ mạng (zip-slip) hoặc khi ghép đường dẫn lấy từ dữ
    liệu bên ngoài. Đây là lỗi bảo mật, không phải lỗi dữ liệu — đừng bắt rồi bỏ qua.
    """


class DataFileError(NostalgiaError):
    """File dữ liệu trên đĩa thiếu, hỏng, hoặc sai cấu trúc."""


class NetworkError(NostalgiaError):
    """Không lấy được dữ liệu qua mạng: kết nối lỗi, mã trả về lạ, hoặc hết thời gian."""


class IntegrityError(NostalgiaError):
    """File tải về không khớp kích thước hoặc sha1 mà máy chủ công bố."""


class VersionError(NostalgiaError):
    """JSON phiên bản sai cấu trúc, thiếu, hoặc kế thừa thành vòng tròn."""


class UnsupportedPlatformError(NostalgiaError):
    """Hệ điều hành không nằm trong ba hệ mà Mojang phát hành cho."""


class Cancelled(NostalgiaError):
    """Người dùng yêu cầu dừng giữa chừng."""
