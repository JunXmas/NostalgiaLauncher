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

`docs/PERFORMANCE.md` có ngân sách đo được và chín luật thiết kế. Bốn điều hay bị vi phạm nhất:

- **Không phụ thuộc runtime.** HTTP dùng `http.client` của thư viện chuẩn. `requests` chạm
  trần ~65 file/s khi chạy song song (phần việc Python của nó dồn vào GIL) trong khi
  `http.client` đạt ~120 file/s và còn tăng theo số luồng.
- **Mặc định 16 luồng**, mỗi luồng một kết nối giữ sống. Không vượt 32 nếu chưa đo lại.
- **Nạp lười mọi thứ nặng** ở tầng lõi: `http.client`, `logging`, `zipfile`,
  `concurrent.futures`, `subprocess`. Riêng `http.client` đắt hơn cả ba thứ sau cộng lại.
- **Băm sha1 trong lúc tải.** sha1 chạy 620 MB/s, mạng 17–25 MB/s — băm khi ghi gần như
  miễn phí, và nhờ đó việc xác minh lần sau bằng kích thước mới đúng đắn về logic.

Đo hiệu năng thì **đừng tin mili-giây tuyệt đối**: máy này chạy `python -c pass` mất 34 ms
khi rảnh và 22 ms khi bận (bộ điều tần CPU). Dùng bội số so với Python trần.

## Cách kiểm — một lượt xanh không đủ

Trước **mỗi** lần báo xong, chạy đủ năm việc dưới đây và **nói rõ đã kiểm cái gì**. Một lượt
chạy xanh không chứng minh được gì; lượt quét đầu tiên ở kho này bắt được ba lỗi thật trong
code vừa viết xong và tưởng đã sạch.

1. **Kiểm cơ bản**
   ```bash
   uv run ruff check . && uv run ruff format --check . && uv run pytest -m "not network" -q
   ```
2. **Quét rác.**
   ```bash
   git ls-files                                        # có file thừa lọt vào không
   grep -rnE 'TODO|FIXME|XXX' $(git ls-files '*.py')   # chỉ soi file nguồn, không soi tài liệu
   uv run ruff check --select F401,F841,ARG,ERA .      # code chết, import thừa, biến bỏ không
   ```
   Rồi soi tay
   code vừa viết tìm **nhánh không bao giờ chạy tới** và **test không thể rớt**
   (kinh điển: bọc `try/except SystemExit` rồi không khẳng định gì).
3. **Chạy lặp.** Bộ test chạy 10–20 lượt, không phải một lượt.
4. **Dựng lại từ đầu.** Clone sạch vào thư mục trắng rồi `uv sync` + test, để bắt thứ chỉ
   chạy được nhờ trạng thái cục bộ.
5. **Đọc log CI thật**, chắc từng bước có chạy chứ không bị bỏ qua.

Số đo hiệu năng phải đo nhiều lượt và ghi thành **khoảng kèm lý do dao động** — không chọn
lần đo đẹp nhất.

Bước nào đụng tới game thật thì phải chạy game và **nhìn bằng mắt** (hoặc chụp ảnh), không
chỉ đọc code.

> Bẫy đã dính: `awk length` đếm **byte** nên dòng tiếng Việt có dấu bị báo quá độ dài sai.
> Đếm ký tự bằng Python.

## Dữ liệu có sẵn trên máy này

`~/.nostalgia-launcher` (7,9 GB) chứa versions 1.8.9 → 1.21.11 kèm bản forge/fabric,
libraries, assets, và JRE Mojang đã tải sẵn (Java 8/17/21/25). Dùng làm **nguồn cắt fixture**
và **kho chỉ-đọc** khi chạy thử, để khỏi tải lại 7,9 GB.

Kho này **không bao giờ mặc định ghi vào đó**. Muốn chạy thử thì trỏ `MCCORE_DATA_DIR` hoặc
`--data-dir` sang thư mục tạm.

## Máy này

Linux Mint 22.3, Python 3.12, `uv` ở `~/.local/bin`. `sudo` đòi mật khẩu nên không cài được
gói hệ thống — mọi thứ phải cài trong home. Không có Java hệ thống (và cũng không cần).
