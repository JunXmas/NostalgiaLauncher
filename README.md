# Nostalgia Launcher

Trình khởi động Minecraft viết bằng Python. Kho này là **phần lõi**: cài đặt và khởi động game
từ dòng lệnh, không giao diện.

Giao diện sẽ được dựng sau, khi lõi đã đứng vững, và chỉ gọi qua façade `nostalgia.api`.

Một cái tên, ba chỗ dùng — không có tên thứ hai cho cùng một thứ:

| Chỗ dùng | Tên |
|---|---|
| Sản phẩm | Nostalgia Launcher |
| Gói Python (`import`) | `nostalgia` |
| Lệnh trên dòng lệnh | `nostalgia` |

## Trạng thái

**Mốc M1 đã xong**: gõ một lệnh là khởi động được Minecraft vanilla với tài khoản offline.

```bash
uv run nostalgia account add-offline Jun     # hoặc: account add-microsoft
uv run nostalgia install 1.20.1          # 3.629 file, 732 MB, 50 giây
uv run nostalgia doctor  1.20.1          # đủ (3.648 mục đã soi)
uv run nostalgia play    1.20.1 --account Jun
```

Đã chạy thật, không phải mô phỏng: cửa sổ Minecraft 1.20.1 và 1.8.9 đều hiện lên (ảnh chụp
trong nhật ký bàn giao). Cài lại lần hai không phát request nào. Ctrl+C giữa lúc tải dừng
sau 0,35 giây và chạy lại tiếp tục được; Ctrl+C lúc đang chơi để lại **0** tiến trình java.

| Bước | Nội dung | Xong |
|---|---|:--:|
| 1 | Khung dự án, từ điển tên, CI | ✅ |
| 2 | `DataPaths`, cách ly đường dẫn, chín test gác | ✅ |
| 3 | Bộ tải file có xác minh sha1 | ✅ |
| 4 | Mô hình phiên bản (rules, kế thừa) — thuần | ✅ |
| 5 | Kho phiên bản (manifest, đọc đĩa trước) | ✅ |
| 6 | client.jar + thư viện + classpath | ✅ |
| 7 | Natives | ✅ |
| 8 | Assets | ✅ |
| 9 | Tải JRE của Mojang | ✅ |
| 10 | Tài khoản offline | ✅ |
| 11 | Dựng lệnh java | ✅ |
| 12 | Chạy và dừng tiến trình game | ✅ |
| 13 | `doctor` — soi mắt xích hỏng | ✅ |
| 14 | Khởi động game thật | ✅ |

Sau M1, đang làm **M2 — đăng nhập Microsoft**:

| Bước | Nội dung | Xong |
|---|---|:--:|
| 15 | `HttpClient` gửi được POST, đọc được thân phản hồi lỗi | ✅ |
| 16 | Bốn chặng đăng nhập: device code → Xbox Live → XSTS → Minecraft | ✅ |
| 17 | Lưu vé làm mới, tự làm mới khi hết hạn | ✅ |
| 18 | `account add-microsoft` và `play` với tài khoản thật | ✅ |

> **Đăng nhập Microsoft cần mã ứng dụng Azure của riêng bạn.** Kho này không nhúng mã nào.
> Đăng ký app ở [portal.azure.com](https://portal.azure.com) (App registrations → *Personal
> Microsoft accounts only* → bật *Allow public client flows*), xin duyệt Minecraft API ở
> [aka.ms/mce-reviewappid](https://aka.ms/mce-reviewappid), rồi đặt
> `NOSTALGIA_MSA_CLIENT_ID=<mã ứng dụng>`.

## Cây thư mục

Tên folder nói **chức năng**, tên file nói **thứ cụ thể**. Không viết tắt.

```
src/nostalgia/
  errors.py            từ vựng lỗi — ở gốc vì mọi tầng đều dùng
  storage/             đĩa: paths.py (cái gì ở đâu) + files.py (đọc/ghi an toàn)
  system/              nhận diện máy: platform_info.py
  operations/          thao tác dài: progress.py + cancellation.py
  model/               dataclass dùng chung: download.py, json_value.py
  version/             THUẦN: rules, maven, meta, inherit — không mạng, không file
  repo/                kho phiên bản: manifest.py + version_repo.py (đĩa trước, mạng sau)
  install/             client/library/assets lập kế hoạch; natives.py giải nén
  java/                bản Java của Mojang: chọn, tải bản nén, bung, dựng liên kết
  account/             tài khoản lưu trên đĩa + danh tính rút ra để dựng lệnh
  launch/              dựng lệnh java + chạy/dừng tiến trình game
  doctor.py            soi bản cài bằng chính kế hoạch của install/
  auth/                đăng nhập Microsoft: bốn chặng, không nhúng mã ứng dụng nào
  cli/                 dòng lệnh — tầng duy nhất được in ra màn hình
  net/                 mạng: http.py (http.client) + download.py (tải song song)
  auth/                đăng nhập Microsoft: bốn chặng, không nhúng mã ứng dụng nào
  cli/                 dòng lệnh — tầng duy nhất được in ra màn hình
tests/                 soi gương cây trên; test soi cả kho nằm ở gốc tests/
bench/                 script đo hiệu năng, không phải test
docs/                  PERFORMANCE.md — ngân sách hiệu năng đo được
```

Sơ đồ đầy đủ bảy tầng và luật phụ thuộc: [GLOSSARY.md](GLOSSARY.md) §5.

## Yêu cầu

Python 3.12 trở lên và [uv](https://docs.astral.sh/uv/). **Không có phụ thuộc runtime nào** —
mọi thứ HTTP dùng `http.client` của thư viện chuẩn. Cũng không cần cài Java: launcher tự tải
JRE của Mojang theo đúng phiên bản game.

## Chạy thử

```bash
uv sync
uv run nostalgia --version
```

## Phát triển

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy                        # kiểm kiểu, strict
uv run pytest -m "not network" -q   # test offline
uv run pytest -m network -q         # test cần Internet
```

Đọc [docs/PERFORMANCE.md](docs/PERFORMANCE.md) để biết ngân sách hiệu năng và bảy luật
thiết kế rút ra từ số đo thật (độ song song, giữ kết nối sống, nạp lười mọi thứ nặng).

Đọc [GLOSSARY.md](GLOSSARY.md) trước khi viết dòng code đầu tiên. Quy ước đặt tên ở đó là
luật; chín test gác ở §4 của file đó biến luật thành thứ CI kiểm được, và cả chín đã
được chứng minh là bắt được vi phạm chứ không chỉ chạy xanh. Quy trình đóng góp xem [CONTRIBUTING.md](CONTRIBUTING.md).
