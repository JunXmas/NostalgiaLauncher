# Quy trình đóng góp

## Một bước, một nhánh, một PR

Kho này cố tình đi chậm. Mỗi PR làm **đúng một bước** trong lộ trình ở README, rồi dừng chờ
duyệt. Không gộp bước, không "tiện tay làm luôn".

Kho tiền nhiệm đi theo cách ngược lại — giao cả cụm việc lớn một lần — và kết quả là 333
commit với sáu cách gọi cùng một hành động, sáu hàm test cho hai mươi hai nghìn dòng, và CI
không chạy test lần nào.

Tên nhánh theo mẫu `step-NN-mô-tả-ngắn`, ví dụ `step-04-version-model`.

## Trước khi mở PR

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -m "not network" -q
```

Cả ba phải xanh. CI chạy đúng ba lệnh này trên mọi PR.

## Mô tả PR phải có

1. **Mục tiêu** — một câu.
2. **Cách kiểm** — lệnh cụ thể đã chạy, kèm kết quả thật. Không viết "đã test kỹ".
3. **Phần bỏ dở** — nếu có, nói thẳng phần nào và vì sao.

## Luật code

Đọc [GLOSSARY.md](GLOSSARY.md). Tóm tắt phần hay bị vi phạm nhất:

- Một khái niệm một tên. Bảng ở mục 2 của GLOSSARY là danh sách đóng.
- `Path` khắp nơi, `str` chỉ ở biên CLI / JSON / `subprocess`.
- Tiền tố hàm cố định: `resolve_` không I/O, `load_` đọc đĩa, `fetch_` chạm mạng,
  `ensure_` idempotent, `plan_` trả việc chứ không tự làm.
- Không hằng `Path` mức module. Không trạng thái toàn cục.
- Mỗi file tối đa 200 dòng.
- Lõi không `print()`. Chỉ `cli/` được in.

## Test

- Mặc định test phải chạy **không cần Internet**. Cần mạng thì đánh `@pytest.mark.network`.
- Dữ liệu vào lấy từ fixture JSON trong `tests/fixture/`, cắt từ file phiên bản thật.
- Test không bao giờ được chạm dữ liệu thật của người dùng — `conftest.py` đã ép `HOME` và
  toàn bộ biến `XDG_*` về thư mục tạm cho mọi test.
