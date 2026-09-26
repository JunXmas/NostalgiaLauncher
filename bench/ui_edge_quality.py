"""Đo độ răng cưa của một ảnh chụp giao diện.

Vì sao cần: "sắc nét hơn" là cảm giác, không kiểm được. Cái đo được là **số bước bậc
thang trên cạnh cong**. Một cạnh bo góc vẽ có khử răng cưa sẽ đi qua nhiều sắc độ trung
gian; vẽ không khử thì nhảy thẳng từ nền sang mặt, tạo bậc.

Cách đo: với mỗi hàng ngang, đếm số pixel có độ sáng NẰM GIỮA nền và mặt (không thuộc hẳn
bên nào). Càng nhiều pixel trung gian quanh một cạnh thì cạnh càng mượt.

    uv run --extra ui python bench/ui_edge_quality.py <ảnh.png> [<vùng x,y,w,h>]

In ra `trung_gian=<n>` — số pixel chuyển tiếp trên toàn vùng.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QImage, qGray


def transition_pixels(image: QImage) -> int:
    """Đếm pixel có độ sáng trung gian giữa hai vùng liền kề.

    Quét ngang: chỗ nào độ sáng đổi hướng mạnh thì đó là một cạnh; pixel ở giữa hai
    thái cực của cạnh đó là pixel khử răng cưa.
    """
    width, height = image.width(), image.height()
    grey = [[qGray(image.pixel(x, y)) for x in range(width)] for y in range(height)]
    count = 0
    for y in range(height):
        for x in range(1, width - 1):
            left, here, right = grey[y][x - 1], grey[y][x], grey[y][x + 1]
            # Nằm hẳn giữa hai hàng xóm, và hai hàng xóm cách nhau đủ xa để là một cạnh
            # thật chứ không phải nhiễu của ảnh nền.
            low, high = min(left, right), max(left, right)
            if high - low >= 24 and low + 6 < here < high - 6:
                count += 1
    return count


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    image = QImage(str(Path(argv[1])))
    if image.isNull():
        print(f"không đọc được ảnh: {argv[1]}", file=sys.stderr)
        return 1
    if len(argv) > 2:
        x, y, w, h = (int(part) for part in argv[2].split(","))
        image = image.copy(x, y, w, h)
    print(f"trung_gian={transition_pixels(image)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
