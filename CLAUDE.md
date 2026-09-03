# mccore — điều lệ kho

## Nhịp làm việc

**Mỗi PR làm đúng một bước** trong lộ trình ở README, rồi **dừng chờ duyệt**. Không gộp bước,
không làm sang bước kế tiếp dù thấy dễ. Chủ dự án cần kịp đọc từng thay đổi.

Nhánh đặt tên `step-NN-mô-tả-ngắn`.

## Luật đặt tên là luật

Đọc `GLOSSARY.md` trước khi viết code. Bảng thuật ngữ ở mục 2 là **danh sách đóng** — cần một
khái niệm mới thì thêm vào từ điển trong cùng PR đó, đừng tự đặt tên rồi đi tiếp.

## Ba điều tuyệt đối không làm

1. **Không hằng `Path` ở mức module.** Không `CONFIG_DIR = Path.home() / ...`. Đường dẫn luôn
   nằm trong `DataPaths` được truyền vào. Đây là nguyên nhân gốc khiến kho tiền nhiệm ghi đè
   config thật của người dùng và làm mất sạch instance.
2. **Không `print()` ngoài `cli/`.** Tiến độ đi qua `on_progress`, diễn biến đi qua `logging`.
3. **Không import ngược tầng.** Sơ đồ tầng ở mục 5 của `GLOSSARY.md`.

Cả ba đều có test gác trong CI từ bước 2.

## Hiệu năng là ràng buộc, không phải chuyện tính sau

`docs/PERFORMANCE.md` có ngân sách đo được và bảy luật thiết kế. Ba luật hay bị vi phạm nhất:
mặc định **16 luồng** tải (32 chậm hơn 16), **một `Session` dùng chung** cho cả đợt (tái dùng
kết nối đáng giá 2–5×), và **nạp `requests` lười** (nó tốn ~200 ms mỗi lần gõ lệnh).

## Cách kiểm

Không báo xong khi chưa chạy thật:

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest -m "not network" -q
```

Bước nào đụng tới game thật thì phải chạy game và **nhìn bằng mắt** (hoặc chụp ảnh), không
chỉ đọc code.

## Dữ liệu có sẵn trên máy này

`~/.nostalgia-launcher` (7,9 GB) chứa versions 1.8.9 → 1.21.11 kèm bản forge/fabric,
libraries, assets, và JRE Mojang đã tải sẵn (Java 8/17/21/25). Dùng làm **nguồn cắt fixture**
và **kho chỉ-đọc** khi chạy thử, để khỏi tải lại 7,9 GB.

Kho này **không bao giờ mặc định ghi vào đó**. Muốn chạy thử thì trỏ `MCCORE_DATA_DIR` hoặc
`--data-dir` sang thư mục tạm.

## Máy này

Linux Mint 22.3, Python 3.12, `uv` ở `~/.local/bin`. `sudo` đòi mật khẩu nên không cài được
gói hệ thống — mọi thứ phải cài trong home. Không có Java hệ thống (và cũng không cần).
