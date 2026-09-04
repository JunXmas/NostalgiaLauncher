# mccore

Lõi launcher Minecraft viết bằng Python. Cài đặt và khởi động game từ dòng lệnh — không giao diện.

Giao diện sẽ được dựng sau, khi lõi đã đứng vững, và chỉ gọi qua façade `mccore.api`.

## Trạng thái

Đang xây tới mốc **M1**: gõ một lệnh là khởi động được Minecraft vanilla với tài khoản offline.

| Bước | Nội dung | Xong |
|---|---|:--:|
| 1 | Khung dự án, từ điển tên, CI | ✅ |
| 2 | `DataPaths`, cách ly đường dẫn, chín test gác | ✅ |
| 3 | Bộ tải file có xác minh sha1 | ✅ |
| 4 | Mô hình phiên bản (rules, kế thừa) — thuần | ✅ |
| 5 | Kho phiên bản (manifest, đọc đĩa trước) | ✅ |
| 6 | client.jar + thư viện + classpath | ✅ |
| 7 | Natives | ✅ |
| 8 | Assets | |
| 9 | Tải JRE của Mojang | |
| 10 | Tài khoản offline | |
| 11 | Dựng lệnh java | |
| 12 | Chạy và dừng tiến trình game | |
| 13 | `doctor` — soi mắt xích hỏng | |
| 14 | Khởi động game thật | |

## Cây thư mục

Tên folder nói **chức năng**, tên file nói **thứ cụ thể**. Không viết tắt.

```
src/mccore/
  errors.py            từ vựng lỗi — ở gốc vì mọi tầng đều dùng
  storage/             đĩa: paths.py (cái gì ở đâu) + files.py (đọc/ghi an toàn)
  system/              nhận diện máy: platform_info.py
  operations/          thao tác dài: progress.py + cancellation.py
  model/               dataclass dùng chung: download.py, json_value.py
  version/             THUẦN: rules, maven, meta, inherit — không mạng, không file
  repo/                kho phiên bản: manifest.py + version_repo.py (đĩa trước, mạng sau)
  install/             client.py + library.py chỉ lập kế hoạch; natives.py giải nén
  net/                 mạng: http.py (http.client) + download.py (tải song song)
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
luật; chín test gác ở §4 của file đó biến luật thành thứ CI kiểm được, và cả chín đã
được chứng minh là bắt được vi phạm chứ không chỉ chạy xanh. Quy trình đóng góp xem [CONTRIBUTING.md](CONTRIBUTING.md).
