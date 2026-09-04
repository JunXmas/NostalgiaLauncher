# Ngân sách hiệu năng

Tài liệu này là **ràng buộc thiết kế**, viết trước khi có code lõi, vì các lựa chọn dưới đây
sửa sau rất đắt. Mọi con số đều do ba script trong `bench/` in ra trên máy phát triển
(Linux Mint 22.3, SSD, đường truyền gia đình). Chạy lại được — mục 6 ghi lệnh cụ thể.

## 0. Hai bẫy đo lường đã trả giá

Đọc mục này trước, nếu không sẽ hiểu sai mọi con số bên dưới.

**Xung nhịp CPU làm số tuyệt đối vô nghĩa.** Cùng một phép đo `python -c pass` cho **34 ms
khi máy rảnh** và **22 ms khi máy đang bận** — bộ điều tần giữ xung thấp lúc nhàn rỗi rồi
boost lên khi có tải, nên máy càng bận đo càng nhanh, ngược hẳn trực giác. Dao động tới 3
lần. Vì vậy ngân sách khởi động ở đây đặt theo **bội số của thời gian khởi động Python
trần**, đo xen kẽ trong cùng một lượt; bội số ổn định (1,75–1,80) trong khi số tuyệt đối
nhảy loạn.

**Cache biên CDN thiên vị cấu hình chạy đầu tiên.** Quét số luồng mà không hâm nóng thì cấu
hình đầu (thường là 1 luồng) chịu toàn bộ cache miss, làm mọi cấu hình sau trông tốt hơn
thực tế. `download_bench.py` hâm nóng một lượt không tính giờ, rồi chạy các cấu hình theo
**thứ tự ngẫu nhiên**.

## 1. Công việc thật lớn cỡ nào

`verify_bench.py` in ra, trên `assets/indexes/5.json` (Minecraft 1.20.1):

| Số liệu | Giá trị |
|---|---|
| Số mục trong index | 3.598 |
| Số hash **duy nhất** | 3.575 (23 mục trùng hash) |
| Tổng dung lượng | 649 MB |
| Kích thước trung vị | 19,3 KB |

Phân bố theo ba dải, đếm **sau dedupe** (1.347 + 1.737 + 491 = 3.575):

| Dải | Số file | Dung lượng |
|---|---:|---:|
| < 16 KB | 1.347 | 13,4 MB |
| 16–64 KB | **1.737** | 49,8 MB |
| ≥ 64 KB | 491 | 585,8 MB |

**Kết luận quan trọng nhất:** 3.084 file (86%) nhỏ hơn 64 KB nhưng cộng lại chỉ 63 MB. Nút
thắt là **số vòng request**, không phải băng thông. Dải giữa 16–64 KB là dải đông nhất theo
số file nên được đo riêng — không ngoại suy từ dải nhỏ.

## 2. Vì sao dùng `http.client` chứ không phải `requests`

Kho này **không có phụ thuộc runtime nào**. Đó không phải chủ nghĩa khổ hạnh, mà là kết quả
đo.

### 2.1 `requests` chạm trần khi chạy song song

Đo xen kẽ, cùng mẫu, cùng CDN:

| Độ song song | `requests` (Session dùng chung) | `http.client` (stdlib) |
|---|---|---|
| 8 luồng | 49,5 file/s | 56,7 file/s |
| 16 luồng | 60,8 file/s | 93,5 file/s |
| 24 luồng | 57,5 file/s | 99,7 file/s |

`requests` **chững lại rồi đi xuống sau 16 luồng**; `http.client` vẫn tăng.

Nguyên nhân, xác định bằng phép đo tuần tự trên một kết nối đã hâm nóng: **102,5 so với
102,4 ms mỗi request** — hai bên **bằng nhau**. Vậy `requests` không hề đắt hơn mỗi request;
mạng che hết. Chênh lệch chỉ xuất hiện khi song song, tức là phần việc Python nặng hơn của
`requests` ở mỗi request bị **dồn vào GIL** và tạo trần cứng.

Đã thử cách cứu hiển nhiên — **mỗi luồng một `Session` riêng** để tránh tranh chấp pool
dùng chung: 71,0 so với 65,1 file/s ở 16 luồng, và 65,4 so với 63,3 ở 24 luồng. **Không
cứu được.** Trần nằm trong đường xử lý của `requests`, không nằm ở pool.

### 2.2 Các phương án khác cũng thua

- **HTTP/2 ghép kênh** (`httpx`, một kết nối): 99,8–111,8 file/s, kém `http.client`, dao
  động mạnh (một lượt 1,07 s, lượt sau 6,81 s), lại thêm hai phụ thuộc. Cả ba host của
  Mojang **đều bật h2** nên phương án này khả thi về kỹ thuật — chỉ là không đáng.
- Giữ `requests`: trả thêm ~1,5× thời gian tải và ~1,5× thời gian khởi động, đổi lấy
  chuyển hướng và retry sẵn có. Đã dò thật: **không host nào của Mojang hay Fabric chuyển
  hướng hoặc nén** (`resources.download`, `launchermeta`, `piston-meta`, `piston-data`,
  `meta.fabricmc.net` — tất cả trả 200/404 thẳng, `Content-Encoding` rỗng). Phần phải tự
  viết vì thế nhỏ.

> Cảnh báo cho các bước sau M1: CurseForge, OptiFine và GitHub **có** chuyển hướng. Khi
> chạm tới chúng, `net/http.py` phải có xử lý 3xx — đừng giả định như với Mojang.

## 3. Đo được gì

### 3.1 Độ song song (dải < 16 KB, 120 file, hâm nóng trước, thứ tự ngẫu nhiên, trung vị 3 lượt)

Hai lượt chạy đầy đủ, cách nhau vài chục phút trên cùng máy và cùng đường truyền:

| Luồng | lượt A (file/s) | lượt B (file/s) |
|---:|---:|---:|
| 1 | 8,9 | 9,2 |
| 4 | 33,4 | 34,7 |
| 8 | 65,0 | 62,8 |
| 16 | 92,4 | 86,6 |
| 24 | 122,1 | **152,3** |
| 32 | 100,2 | **78,0** |
| 48 | 143,5 | **174,6** |

Đọc đúng bảng này: **từ 1 lên 16 luồng là mười lần, không bàn cãi** — hai lượt khớp nhau
trong vòng 7%. Từ 16 trở lên, hai lượt **mâu thuẫn nhau**: 32 luồng lúc thì 100 lúc thì 78,
còn 48 luồng lúc 143 lúc 175. Một lượt quét thứ ba cho 16→120, 24→120, 32→123, 48→98, 64→73.

Ba lượt, ba hình dạng khác nhau ở vùng trên. Kết luận trung thực duy nhất rút ra được:
**tăng mạnh tới ~16 luồng, sau đó là nhiễu, và suy giảm khi lên rất cao.** Phép đo này
*không* đủ để nói 24 tốt hơn 32 hay 48 tốt hơn 24 — ai khẳng định thế là đọc quá dữ liệu.

Vì vậy **không chốt một con số "tối ưu"**. Chốt: mặc định 16 (điểm cuối cùng còn đo được
chắc chắn), cho phép chỉnh, và **không vượt 32 nếu chưa đo lại trên đường truyền cụ thể**.

### 3.2 Hai dải còn lại

| Dải | 8 luồng | 16 luồng | 24 luồng |
|---|---:|---:|---:|
| 16–64 KB (60 file, 1,6 MB) | 46,3 file/s | 17,1 file/s | 70,3 file/s |
| ≥ 64 KB (24 file, 39,1 MB) | 28,1 MB/s | 31,1 MB/s | 33,2 MB/s |

Dải giữa cũng nhiễu như dải nhỏ (con số 17,1 ở 16 luồng là một lượt tậm tịt, không phải quy
luật). Dải lớn thì ổn định và bão hoà băng thông từ 8 luồng — băng thông đo được dao động
17–33 MB/s giữa các phiên tuỳ chất lượng đường truyền.

### 3.3 Tái dùng kết nối

Cùng 16 luồng: giữ kết nối **113,8 file/s** so với mở mới mỗi file **39,4 file/s** →
**2,9×**. Các lượt khác cho 2,1×–4,8×. Hệ số dao động theo mạng nhưng **chưa lần nào đi
ngược** — đây là kết luận chắc chắn nhất trong cả tài liệu, chắc hơn cả con số độ song song.

### 3.4 Xác minh: `stat` so với `sha1`, và kích thước khối đọc

3.575 file, 649 MB: `stat` **104 ms**, `sha1` toàn bộ **1,05 s** (620 MB/s) → chênh **10×**.

Con số `stat` là trên cache metadata **đã nóng**; lần chạy đầu sau khi bật máy sẽ chậm hơn.
Không đo được số nguội vì `drop_caches` cần quyền root.

Kích thước khối đọc **gần như không ảnh hưởng tốc độ** — đo trên 400 file thật:

| Khối | MB/s |
|---|---:|
| 64 KiB | 500 |
| 256 KiB | 510 |
| 1 MiB | 511 |
| 4 MiB | 504 |
| 16 MiB | 503 |
| `hashlib.file_digest` | **470** |

Nên chọn **256 KiB**: cùng tốc độ nhưng khi băm song song 16 luồng chỉ tốn 4 MiB bộ đệm thay
vì 16 MiB. Và `hashlib.file_digest` (có sẵn từ Python 3.11) **chậm hơn** với nhiều file nhỏ —
ghi lại để không ai "hiện đại hoá" sang nó rồi thành tụt hiệu năng.

### 3.5 Khởi động CLI (bội số của Python trần, đo xen kẽ 15 lượt)

| Phép đo | Bội số |
|---|---:|
| `python -c pass` | 1,00× |
| `import nostalgia` | **1,01×** |
| `import nostalgia.cli.main` | 1,41× |
| **`nostalgia --version` trọn vẹn** | **1,80×** |
| + `http.client` | **2,89×** |
| + `zipfile` | 2,12× |
| + `concurrent.futures` | 2,03× |
| + `logging` | 1,97× |
| + `subprocess` | 1,73× |
| + tất cả những thứ trên | **3,89×** |

`import nostalgia` gần như miễn phí (1,01×) — giữ được điều đó là mục tiêu, không phải may mắn.

**Điều quan trọng hơn:** kẻ đắt nhất là `http.client` (+1,48× so với `cli.main`), **đắt hơn
cả `logging` + `zipfile` + `concurrent.futures` cộng lại**. Bỏ `requests` không giải quyết
xong vấn đề — nó chỉ đổi tên kẻ thủ phạm. Luật phải là *nạp lười mọi thứ nặng*, không phải
*nạp lười một thư viện cụ thể*.

### 3.6 Ghép đường dẫn an toàn: 177 µs xuống 6,5 µs

`resolve_within` được gọi một lần cho **mỗi entry** khi giải nén natives, JRE hay modpack.
Bản đầu dùng `Path.resolve()` hai lần mỗi lần gọi:

| Thành phần | µs/lần |
|---|---:|
| `base.resolve()` | 35,4 |
| `(base / relative).resolve()` | 78,9 |
| `PureWindowsPath(relative).root` / `.drive` | 3,7 |
| **tổng bản cũ** | **176,7** |
| kiểm bằng chuỗi thuần | 0,7 |
| `base.joinpath(*parts)` | 3,1 |
| **tổng bản mới** | **6,5** |

Với một modpack 3.500 file: **618 ms xuống 23 ms**, nhanh hơn 27 lần — chỉ để kiểm tên file.

Bản mới còn **kiểm chặt hơn**: `resolve()` chỉ so đích cuối cùng nên `a/../b.txt` được cho
qua, còn bản chuỗi từ chối mọi thành phần `..`. Không entry archive lành mạnh nào cần `..`.

Đánh đổi: hàm không còn phát hiện symlink đã có sẵn *bên trong* thư mục đích. Bất biến người
gọi phải giữ: **không bao giờ tạo symlink từ nội dung archive** — khi mọi thư mục đều do ta
tạo, không có symlink nào tồn tại để đi qua. Có test ghi rõ giới hạn này.

## 4. Ngân sách

### Ngân sách đường nhanh đã được nới từ 2,0× lên 2,5×, và vì sao

Con số 1,80× ghi ở bước 1 là của một CLI **chưa có lệnh con nào** — chỉ `--version` và
`--help`. Khi bước 14 gắn năm lệnh con vào, đo lại được **3,66×**. Đã truy và cắt phần cắt
được:

| Nguồn chi phí | Đo được | Xử lý |
|---|---|---|
| `CliContext` kéo theo `dataclasses` → `inspect` | ~1,4× | **Cắt** — nạp lười trong `main()` |
| Các module lệnh kéo theo `http.client`, `ssl`, `zipfile`, `subprocess` | có trong 3,66× | **Cắt** — nạp lười trong `run()` |
| `import argparse` | ~13 ms | Không cắt được nếu còn dùng argparse |
| Dựng 5 lệnh con | 4,2 ms, trong đó 2,1 ms là bộ máy của chính argparse | Không cắt được |

Còn **2,23×**. Phần dư là chi phí của chính argparse, nên ngân sách được đặt lại ở 2,5× —
nới có chủ đích kèm số đo, không phải nới để test khỏi đỏ. Hai test gác vẫn chặn việc
`http.client`, `ssl`, `zipfile`, `concurrent.futures`, `subprocess` hay `logging` lọt vào
đường nhanh, vì đó mới là thứ dễ tái phát.

### Vì sao ngân sách phải chia theo loại lệnh

`dataclasses` — thứ GLOSSARY bắt buộc dùng cho mọi kiểu dữ liệu — là import **đắt nhất** đo
được, hơn cả `http.client`:

| Phép đo | Bội số nền |
|---|---:|
| `import dataclasses` | 1,97× |
| định nghĩa 8 dataclass | **2,34×** |
| định nghĩa 8 NamedTuple | 1,58× |
| định nghĩa 8 class thường có `__slots__` | **1,04×** |

Riêng việc khai tám dataclass đã vượt mốc 2,0×. Nhưng đổi sang class viết tay để tiết kiệm
30 ms là đánh đổi sai: mất `frozen`, mất `__eq__`/`__repr__` tự động, và đổi lấy hàng trăm
dòng lặp lại — trong khi 30 ms chỉ đáng kể với lệnh không làm gì cả.

Nên **giữ dataclass**, và chia ngân sách theo loại lệnh. Đường nhanh (`--version`, `--help`)
không chạm tới model nên vẫn giữ được 1,80×; điều đó có test gác.

| Thao tác | Ngân sách |
|---|---|
| `nostalgia --version` / `--help` (không chạm model, không I/O) | **≤ 2,5× khởi động Python trần** (hiện 2,23×) |
| Lệnh chỉ đọc đĩa (`doctor`, liệt kê bản đã cài) | ≤ 4,0× |
| Lệnh chạm mạng | không đặt ngân sách khởi động — mạng chi phối hoàn toàn |
| Xác minh bản cài đầy đủ (theo kích thước) | ≤ 2× số đo `stat` hiện tại, tức ≈ 200 ms |
| Xác minh sâu (sha1 649 MB) | ≤ 2 s, **chỉ khi có cờ** |
| Cài lại khi đã đủ file | **0 request mạng** |
| Cài nguội trọn vẹn 1.20.1 | ≤ 2 phút trên đường truyền ~20 MB/s |
| Từ `play` tới lúc tiến trình java được sinh | ≤ 3× khởi động Python trần |

Ước tính cài nguội, cộng theo **từng dải đã đo riêng**, dùng số thận trọng của 16–24 luồng:

| Phần | Cách tính | Giây |
|---|---|---:|
| asset < 16 KB | 1.347 ÷ ~100 file/s | 13 |
| asset 16–64 KB | 1.737 ÷ ~70 file/s | 25 |
| asset ≥ 64 KB | 585,8 MB ÷ ~25 MB/s | 23 |
| thư viện + client.jar + JRE | ~185 MB ÷ ~25 MB/s, cộng ~220 vòng request | 9 |
| | **tổng** | **≈ 70** |

Băng thông dao động 17–33 MB/s giữa các phiên, nên khoảng thật là **65–95 giây**. Ngân sách
đặt ở 2 phút để còn chỗ cho đường truyền kém hơn.

Một luồng thì riêng phần asset đã là 3.575 ÷ ~9 ≈ **6,6 phút**.

## 5. Chín luật thiết kế

1. **Mặc định 16 luồng**, cho phép chỉnh. Không vượt 32 nếu chưa đo lại (mục 3.1).
2. **Giữ kết nối sống.** Mỗi luồng một `http.client.HTTPSConnection` bền, dùng lại cho
   nhiều request, dựng lại khi phía kia đóng. Không mở kết nối mới cho từng file (2,4×).
3. **Gói `net/` độc quyền giữ kiến thức về HTTP, và đường nhanh của CLI không chạm `net/`.**
   Bản đầu của luật này viết là "không module nào ở tầng lõi được import `http.client`" —
   nhưng chính `net/http.py` buộc phải import nó, nên luật đó không đúng theo mặt chữ. Luật
   kiểm được: `http.client` và `ssl` chỉ xuất hiện trong `net/`; và sau khi chạy
   `nostalgia --version` thì `sys.modules` không được có `http.client`, `ssl`, `zipfile`,
   `concurrent.futures`, `subprocess`, `logging`. CLI phải phân giải lệnh con **sau khi**
   parse đối số, không import sẵn mọi lệnh. Cả hai nửa đều có test gác.
4. **Xác minh mặc định bằng kích thước**, sha1 chỉ khi có cờ hoặc khi file đã lộ ra là hỏng.
5. **Băm sha1 *trong lúc* tải.** Byte đang nằm trong RAM; sha1 chạy 620 MB/s còn mạng
   17–25 MB/s, nên băm khi ghi tốn dưới 5% một lõi — gần như miễn phí. Nhờ đó luật 4 trở
   nên **đúng đắn về mặt logic** (mọi file đã được băm đúng một lần lúc sinh ra) chứ không
   chỉ là đánh đổi rủi ro.
6. **Ghi nguyên tử.** Tải ra `.part`, `fsync`, rồi `os.replace`. Không có nó, một lần Ctrl-C
   để lại file cụt mà luật 4 không phải lúc nào cũng bắt được.
7. **Dedupe theo hash trước khi lập danh sách tải.** 23 mục trùng ở index 1.20.1; quan
   trọng hơn là nó chặn hai luồng cùng ghi vào một đích.
8. **Bỏ qua file đã đúng.** Lần cài thứ hai phải không phát request nào.
9. **Retry có backoff và deadline tổng.** CDN trả 5xx và reset kết nối là chuyện thường.
   `timeout` của socket không phải deadline cho cả request — phải có deadline riêng, và
   phải tôn trọng `CancelToken`.

## 6. Cách đo lại

```bash
uv run python bench/verify_bench.py       # phân bố kích thước + chi phí xác minh (không cần mạng)
uv run python bench/startup_bench.py      # bội số khởi động CLI (không cần mạng)
uv run python bench/download_bench.py     # độ song song, ba dải, tái dùng kết nối (cần mạng)
uv run python bench/download_bench.py --count 60 --runs 5   # mẫu nhỏ hơn, nhiều lượt hơn
```

Các script không phải test: chúng in số đo để người đọc so, không tự khẳng định đậu/rớt.
Ngân sách ở mục 4 sẽ thành test thật khi các bước tương ứng có code — bước 3 cho tải, bước
13 cho xác minh, bước 14 cho khởi động.
