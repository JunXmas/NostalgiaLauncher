"""Điểm vào của bản đã đóng gói (PyInstaller).

Bản chạy từ mã nguồn vào bằng `python -m nostalgia gui`, nhưng bản đóng gói thì
không có dòng lệnh để gõ: người dùng bấm vào biểu tượng và chỉ mong thấy cửa sổ.
Nên file này bỏ hẳn lớp argparse, chỉ còn đúng việc mở giao diện.

Vẫn nhận `--version` để ai muốn tạo shortcut nhảy thẳng vào một phiên bản thì làm
được, nhưng không có tham số nào cũng chạy tốt.
"""

from __future__ import annotations

import multiprocessing
import sys


def main() -> int:
    # Bắt buộc phải gọi trước mọi thứ khác trên Windows và macOS: bản đóng gói
    # khởi động tiến trình con bằng cách chạy lại chính file thực thi này, nên
    # thiếu freeze_support() thì mỗi tiến trình con lại mở thêm một cửa sổ
    # launcher — nhân lên vô hạn cho tới khi hết RAM.
    multiprocessing.freeze_support()

    from nostalgia.paths import migrate_legacy
    from nostalgia.ui.app import run_gui

    migrate_legacy()
    version = ""
    if "--version" in sys.argv:
        index = sys.argv.index("--version")
        if index + 1 < len(sys.argv):
            version = sys.argv[index + 1]
    return run_gui(None, version)


if __name__ == "__main__":
    sys.exit(main())
