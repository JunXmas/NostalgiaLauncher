# mccore

Lõi launcher Minecraft viết bằng Python. Cài đặt và khởi động game từ dòng lệnh — không giao diện.

Giao diện sẽ được dựng sau, khi lõi đã đứng vững, và chỉ gọi qua façade `mccore.api`.

## Trạng thái

Đang xây tới mốc **M1**: gõ một lệnh là khởi động được Minecraft vanilla với tài khoản offline.

| Bước | Nội dung | Xong |
|---|---|:--:|
| 1 | Khung dự án, từ điển tên, CI | ✅ |
| 2 | `DataPaths`, cách ly đường dẫn, ba test gác | |
| 3 | Bộ tải file có xác minh sha1 | |
| 4 | Mô hình phiên bản (rules, kế thừa) — thuần | |
| 5 | Kho phiên bản (manifest, đọc đĩa trước) | |
| 6 | client.jar + thư viện + classpath | |
| 7 | Natives | |
| 8 | Assets | |
| 9 | Tải JRE của Mojang | |
| 10 | Tài khoản offline | |
| 11 | Dựng lệnh java | |
| 12 | Chạy và dừng tiến trình game | |
| 13 | `doctor` — soi mắt xích hỏng | |
| 14 | Khởi động game thật | |

## Yêu cầu

Python 3.12 trở lên và [uv](https://docs.astral.sh/uv/). **Không có phụ thuộc runtime nào** —
mọi thứ HTTP dùng `http.client` của thư viện chuẩn. Cũng không cần cài Java: launcher tự tải
JRE của Mojang theo đúng phiên bản game.

## Chạy thử

```bash
uv sync
uv run mccore --version
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
luật; bảy test gác được liệt kê ở §4 của file đó, tất cả sẽ có từ bước 2 trở đi —
hiện tại (bước 1) chưa test nào tồn tại. Quy trình đóng góp xem [CONTRIBUTING.md](CONTRIBUTING.md).
