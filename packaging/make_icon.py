"""Vẽ biểu tượng ứng dụng rồi xuất ra .png, .ico và .icns.

Vì sao tự vẽ thay vì để sẵn file ảnh: biểu tượng cần đủ mọi cỡ từ 16 tới 1024,
và mỗi hệ điều hành đòi một định dạng chứa khác nhau. Sinh bằng mã thì mọi cỡ
luôn khớp nhau, sửa màu một chỗ là cả bộ đổi theo, và kho không phải ôm hai chục
file nhị phân.

Hai định dạng chứa được viết tay ở đây thay vì gọi thư viện ngoài:

* **.ico** — dùng DIB 32-bit cho các cỡ nhỏ và PNG cho 128/256. Đây là cách bố
  trí lai mà chính Windows dùng: một số chỗ trong shell đời cũ vẫn không đọc
  được mục nén PNG cỡ nhỏ, còn nhúng 256×256 dạng DIB thì file phồng lên vô ích.
* **.icns** — container của Apple, đơn giản tới mức viết tay còn gọn hơn đi cài
  thêm thư viện. Trên máy macOS thì `build-macos.sh` vẫn ưu tiên `iconutil` của
  hệ thống, xem đó là chuẩn mực; hàm ở đây lo cho mọi máy còn lại.

Chạy: python packaging/make_icon.py [thư-mục-ra]
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter

# Cỡ nào cũng vẽ lại từ bản logo gốc phân giải cao rồi thu nhỏ mượt, để mọi cỡ
# đều khớp nhau và luôn theo đúng logo của launcher.
SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)

# Logo ứng dụng: khối lá xanh dùng khắp giao diện (nostalgia/ui/assets/logo.png).
LOGO_PATH = Path(__file__).resolve().parent.parent / "nostalgia" / "ui" / "assets" / "logo.png"
_LOGO: QImage | None = None


def _logo() -> QImage:
    global _LOGO
    if _LOGO is None:
        img = QImage()
        if not img.load(str(LOGO_PATH)):
            raise FileNotFoundError(f"Không đọc được logo: {LOGO_PATH}")
        _LOGO = img.convertToFormat(QImage.Format_ARGB32)
    return _LOGO


def draw(size: int) -> QImage:
    """Kết xuất logo lá của launcher ra một cỡ, căn giữa, giữ tỉ lệ, nền trong suốt."""
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    src = _logo()
    # Chừa lề nhỏ để logo không chạm sát mép khung icon.
    margin = size * 0.04
    box = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    side = min(box.width(), box.height())
    dst = QRectF(box.center().x() - side / 2, box.center().y() - side / 2, side, side)
    p.drawImage(dst, src, QRectF(src.rect()))
    p.end()
    return image


def png_bytes(image: QImage) -> bytes:
    # QBuffer chỉ giữ con trỏ tới QByteArray chứ không sở hữu nó, nên mảng phải
    # là một biến sống trong suốt lúc ghi. Viết QBuffer(QByteArray()) thì mảng
    # tạm bị thu gom ngay và tiến trình chết vì segfault, không kịp báo lỗi.
    store = QByteArray()
    buffer = QBuffer(store)
    buffer.open(QBuffer.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(store)


def _dib_bytes(image: QImage) -> bytes:
    """Đóng một ảnh thành DIB 32-bit đúng kiểu .ico đòi hỏi.

    Ba chỗ dễ sai và đều làm Windows từ chối cả file: header khai chiều cao gấp
    đôi (vì tính cả mặt nạ AND nằm ngay sau), điểm ảnh xếp từ dưới lên, và mặt
    nạ AND phải đệm cho mỗi dòng tròn 4 byte dù ta không dùng tới nó — độ trong
    suốt đã nằm sẵn trong kênh alpha.
    """
    img = image.convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()

    header = struct.pack(
        "<IiiHHIIiiII",
        40,        # kích thước BITMAPINFOHEADER
        w, h * 2,  # chiều cao gấp đôi: XOR ở dưới, AND ở trên
        1, 32,     # planes, bits per pixel
        0,         # BI_RGB, không nén
        w * h * 4, 0, 0, 0, 0,
    )

    rows = []
    for y in range(h - 1, -1, -1):           # từ dưới lên
        row = bytearray()
        for x in range(w):
            c = img.pixelColor(x, y)
            row += bytes((c.blue(), c.green(), c.red(), c.alpha()))
        rows.append(bytes(row))

    mask_stride = ((w + 31) // 32) * 4       # 1 bit mỗi điểm, tròn 4 byte mỗi dòng
    mask = b"\x00" * (mask_stride * h)
    return header + b"".join(rows) + mask


def write_ico(images: dict[int, QImage], dest: Path) -> None:
    """Ghi .ico gồm nhiều cỡ. Cỡ ≥128 nhúng PNG, còn lại nhúng DIB."""
    entries, blobs = [], []
    offset = 6 + 16 * len(images)
    for size in sorted(images):
        data = png_bytes(images[size]) if size >= 128 else _dib_bytes(images[size])
        entries.append(struct.pack(
            "<BBBBHHII",
            size if size < 256 else 0,       # 256 được mã hoá thành 0
            size if size < 256 else 0,
            0, 0, 1, 32,
            len(data), offset,
        ))
        blobs.append(data)
        offset += len(data)

    with dest.open("wb") as f:
        f.write(struct.pack("<HHH", 0, 1, len(images)))
        for entry in entries:
            f.write(entry)
        for blob in blobs:
            f.write(blob)


# Mỗi cỡ trong .icns mang một mã bốn ký tự riêng. Cùng một số điểm ảnh có thể
# xuất hiện hai lần dưới hai mã khác nhau — bản thường và bản Retina @2x — và
# macOS cần cả hai thì mới hiển thị sắc nét ở mọi nơi.
ICNS_TYPES = {
    b"icp4": 16, b"icp5": 32, b"icp6": 64,
    b"ic07": 128, b"ic08": 256, b"ic09": 512, b"ic10": 1024,
    b"ic11": 32, b"ic12": 64, b"ic13": 256, b"ic14": 512,
}


def write_icns(images: dict[int, QImage], dest: Path) -> None:
    chunks = b""
    for code, size in ICNS_TYPES.items():
        if size not in images:
            continue
        data = png_bytes(images[size])
        chunks += code + struct.pack(">I", len(data) + 8) + data
    dest.write_bytes(b"icns" + struct.pack(">I", len(chunks) + 8) + chunks)


def main(out_dir: Path) -> None:
    # QImage/QPainter cần một QGuiApplication tồn tại, kể cả khi không mở cửa sổ.
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    out_dir.mkdir(parents=True, exist_ok=True)

    images = {size: draw(size) for size in SIZES}

    iconset = out_dir / "Nostalgia.iconset"
    iconset.mkdir(exist_ok=True)
    for size, image in images.items():
        image.save(str(out_dir / f"icon-{size}.png"), "PNG")
        # Tên file trong .iconset là quy ước cứng của `iconutil`, sai một chữ là
        # nó bỏ qua cỡ đó không báo lỗi.
        image.save(str(iconset / f"icon_{size}x{size}.png"), "PNG")
        if size % 2 == 0 and size // 2 in SIZES:
            image.save(str(iconset / f"icon_{size // 2}x{size // 2}@2x.png"), "PNG")

    write_ico({s: images[s] for s in (16, 24, 32, 48, 64, 128, 256)}, out_dir / "icon.ico")
    write_icns(images, out_dir / "icon.icns")
    images[256].save(str(out_dir / "icon.png"), "PNG")

    print(f"Icons written to {out_dir}")
    del app


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "assets"
    main(target)
