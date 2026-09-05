"""Một bản chơi: tên, phiên bản, và vài tuỳ chọn riêng.

**Điều quyết định của M3**: mỗi instance có thư mục chơi riêng, nhưng `versions/`,
`libraries/`, `assets/` và `runtime/` thì **dùng chung**. Chép kho cho từng instance là nhân
700 MB lên theo số bản chơi; còn trộn chung thư mục chơi là bản mới ăn thế giới của bản cũ.

Mã instance là **một đoạn đường dẫn**, do người dùng gõ, nên nó bị kiểm hai lớp: mẫu ở đây
cho thông báo lỗi đọc được, và `resolve_child` ở `DataPaths` chặn mọi lối thoát ra ngoài.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from nostalgia.errors import InstanceError

# Chữ cái/chữ số mở đầu để không có tên bắt đầu bằng dấu chấm (file ẩn) hay dấu gạch (trông
# như tham số dòng lệnh). 64 ký tự là dư cho tên người đặt, và an toàn với mọi hệ thống file.
INSTANCE_ID_PATTERN = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


@dataclass(frozen=True, slots=True)
class Instance:
    """Một bản chơi đã đăng ký."""

    instance_id: str
    version_id: str
    display_name: str = ""
    max_heap_megabytes: int | None = None
    window_width: int | None = None
    window_height: int | None = None

    @property
    def label(self) -> str:
        """Tên để hiển thị; chưa đặt thì dùng chính mã instance."""
        return self.display_name or self.instance_id


def check_instance_id(instance_id: str) -> str:
    """Kiểm mã instance và trả lại chính nó, để dùng ngay trong biểu thức."""
    if INSTANCE_ID_PATTERN.match(instance_id) is None:
        message = (
            f"mã instance {instance_id!r} không hợp lệ: bắt đầu bằng chữ cái hoặc chữ số, "
            "sau đó chỉ gồm chữ cái, chữ số, dấu chấm, gạch ngang, gạch dưới; tối đa 64 ký tự"
        )
        raise InstanceError(message)
    return instance_id
