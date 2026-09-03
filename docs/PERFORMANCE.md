# Ngân sách hiệu năng

Tài liệu này là **ràng buộc thiết kế**, viết trước khi có code lõi, vì các lựa chọn dưới đây
sửa sau rất đắt. Mọi con số đều đo thật trên máy phát triển (Linux Mint 22.3, SSD, đường
truyền ~24 MB/s), bằng hai script trong `bench/`. Chạy lại được.

## 1. Công việc thật lớn cỡ nào

Đo trên `assets/indexes/5.json` — chỉ mục asset của Minecraft 1.20.1:

| Số liệu | Giá trị |
|---|---|
| Số mục trong index | 3.598 |
| Số hash **duy nhất** | 3.575 (→ 23 mục trùng hash) |
| Tổng dung lượng | 649 MB |
| Kích thước trung vị | 19,2 KB |
| File < 64 KB | **3.107 file (86%) nhưng chỉ chiếm 63 MB** |
| File ≥ 64 KB | 468 file, chiếm 586 MB |

**Kết luận quan trọng nhất:** phần lớn công việc là **hàng nghìn file nhỏ**. Nút thắt là **số
vòng request**, không phải băng thông. Mọi tối ưu phải nhắm vào đó.

## 2. Đo được gì

### 2.1 Tải: độ song song và tái dùng kết nối

120 file nhỏ (<16 KB, tổng 1,2 MB) từ `resources.download.minecraft.net`, hai lượt đo:

| Cấu hình | Tốc độ | So với 1 luồng |
|---|---|---|
| 1 luồng | 8,9–9,4 file/s | 1,0× |
| 4 luồng | 29,4–34,9 file/s | ~3,5× |
| 8 luồng | 58,2–63,5 file/s | ~6,6× |
| **16 luồng** | **77,3–81,2 file/s** | **~8,7×** |
| 32 luồng | 58,6–70,0 file/s | ~7× — **chậm hơn 16** |

Tất cả các dòng trên đều dùng lại kết nối. **16 luồng là điểm tối ưu; 32 luồng *chậm hơn*
16** ở cả hai lượt đo — thêm luồng nữa là hại, không phải lợi.

Về tái dùng kết nối, đo riêng bằng 3 cặp xen kẽ (để loại nhiễu mạng theo thời điểm), 60 file,
cùng 16 luồng:

| Cặp | Dùng lại kết nối | Kết nối mới mỗi file | Nhanh hơn |
|---|---|---|---|
| 1 | 34,9 file/s | 7,3 file/s | 4,8× |
| 2 | 50,6 file/s | 24,6 file/s | 2,1× |
| 3 | 53,9 file/s | 24,5 file/s | 2,2× |

**Tái dùng kết nối đáng giá 2–5×** ở cùng độ song song; hệ số dao động theo chất lượng mạng
nhưng chưa lần nào đi ngược. Dùng một `requests.Session` với `HTTPAdapter(pool_maxsize=workers)`
cho cả đợt tải, không tạo mới từng file.

File lớn (24 file, 41,9 MB) bão hoà băng thông từ 8 luồng: 22,2 → 25,8 → 23,6 MB/s tương ứng
4 → 8 → 16 luồng. Nghĩa là 16 luồng an toàn cho cả hai loại.

### 2.2 Xác minh: `stat` so với `sha1`

3.575 file asset đã có trên đĩa (649 MB), 4 lượt đo:

| Cách | Thời gian |
|---|---|
| Chỉ `stat` (so kích thước) | **~61 ms** (dao động 60–103 ms) |
| `sha1` toàn bộ | **~1,3 s** (dao động 1,23–1,37 s; 473–527 MB/s) |

Chênh khoảng **20 lần**. Khoảng dao động là do bộ đệm trang của hệ điều hành — lượt đo trên
đĩa nguội chậm hơn rõ rệt, nên con số thật khi người dùng mới bật máy còn tệ hơn.

Nên: mặc định xác minh bằng kích thước; chỉ băm sha1 khi người dùng yêu cầu
(`--verify-hashes`) hoặc khi file đã lộ ra là hỏng.

### 2.3 Khởi động CLI

Trung vị của 7 lượt, đo trọn tiến trình con (kể cả thời gian khởi động thông dịch — đúng
thứ người dùng phải chờ):

| Phép đo | Thời gian |
|---|---|
| Python trần (`python -c pass`) | 34 ms |
| `import mccore` | 35 ms |
| `import mccore.cli.main` | 49 ms |
| **`import requests`** | **272 ms** (riêng phần nạp thư viện: trung vị 198 ms, dao động 166–209 ms) |
| `mccore --version` trọn vẹn, chưa có `requests` | **62 ms** |
| CLI lõi cũ (`nostalgia --help`), có nạp `requests` | 190–280 ms |

**Phần lớn độ trễ khởi động CLI là do nạp `requests`** — kể cả với những lệnh không hề chạm
mạng (`doctor`, `account list`, `play --offline`, liệt kê bản đã cài). Khung CLI hiện tại của
mc-core chạy trong 62 ms chính vì chưa đụng tới `requests`; giữ được điều đó là một mục tiêu,
không phải may mắn.

## 3. Ngân sách — mục tiêu của mc-core

| Thao tác | Ngân sách | Lõi cũ hiện tại |
|---|---|---|
| Khởi động CLI cho lệnh **không chạm mạng** | ≤ 80 ms | 190–280 ms |
| Xác minh bản cài đầy đủ (theo kích thước) | ≤ 150 ms | — |
| Xác minh sâu (sha1 649 MB) | ≤ 2 s, **chỉ khi có cờ** | — |
| Cài lại khi đã đủ file (không-làm-gì) | ≤ 300 ms và **0 request mạng** | — |
| Cài nguội trọn vẹn 1.20.1 trên đường 24 MB/s | ≤ 2 phút | — |
| Từ lệnh `play` tới lúc tiến trình java được sinh | ≤ 400 ms (không tính JVM tự khởi động) | — |

Ước tính cài nguội theo số đo: 3.107 file nhỏ ÷ ~79 file/s ≈ 39 s, cộng 586 MB ÷ ~25 MB/s
≈ 23 s, cộng thư viện, client.jar và JRE ≈ 15 s → **khoảng 80 giây**. Thiết kế một luồng sẽ
mất khoảng **7 phút** cho đúng công việc đó — chậm hơn hơn **5 lần**, và đó là trước khi tính
tới việc không tái dùng kết nối.

## 4. Bảy luật thiết kế rút ra

1. **Mặc định 16 luồng tải**, cho phép chỉnh. Không vượt quá 16 nếu chưa đo lại — 32 chậm hơn.
2. **Một `Session` dùng chung cho cả đợt**, `HTTPAdapter(pool_connections=workers,
   pool_maxsize=workers)`. Tuyệt đối không `requests.get()` trần trong vòng lặp.
3. **Nạp `requests` lười.** `net/http.py` chỉ được import khi thật sự chạm mạng. Không module
   nào ngoài `net/` được import `requests` — luật này đã có test gác, và nó vừa giữ kiến trúc
   sạch vừa cắt 170 ms khỏi mỗi lần gõ lệnh.
4. **Xác minh mặc định bằng kích thước**, sha1 chỉ khi có cờ hoặc khi file đã lộ ra là hỏng.
5. **Dedupe theo hash trước khi lập danh sách tải.** Index 1.20.1 có 23 mục trùng; ngoài
   việc tiết kiệm, nó còn chặn hai luồng cùng ghi vào một file đích.
6. **Bỏ qua file đã đúng.** Lần cài thứ hai phải gần như không phát request nào.
7. **Stream file lớn** (`iter_content`), không `r.content` — 586 MB không được nạp vào RAM.

## 5. Cách đo lại

```bash
uv run python bench/download_bench.py    # cần mạng
uv run python bench/verify_bench.py      # cần dữ liệu asset có sẵn trên đĩa
uv run python bench/startup_bench.py     # đo độ trễ khởi động CLI
```

Các script không phải là test: chúng in số đo để người đọc so, không tự khẳng định đậu/rớt.
Ngân sách ở mục 3 sẽ được biến thành test thật khi các bước tương ứng có code (bước 3 cho
tải, bước 13 cho xác minh, bước 14 cho khởi động).
