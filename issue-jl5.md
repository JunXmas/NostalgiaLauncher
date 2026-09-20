Người dùng report: chạy game trên Windows hiện cửa sổ console Java. Phần khởi động game đã vá ở `7aa34ef` (`CREATE_NO_WINDOW` trong `src/nostalgia/launch/game_process.py`), nhưng đường cài Forge thì chưa.

## Việc cần làm

`src/nostalgia/modloader/forge.py:173` gọi `subprocess.run([str(java_binary), "-jar", ...])` không truyền `creationflags`. Trên Windows, bản đóng gói chạy `console=False` nên tiến trình cha không có console; `java.exe` là app console nên Windows cấp cho nó một cửa sổ CMD mới. Người dùng cài Forge sẽ thấy cửa sổ đen bật lên suốt thời gian installer chạy.

Dùng lại `resolve_creation_flags` đã có sẵn ở `src/nostalgia/launch/game_process.py:60` thay vì viết hằng số mới. Nếu import chéo module thấy sai chỗ thì đề xuất trong bình luận, đừng tự dựng thêm module mới.

Lưu ý `CREATE_NEW_PROCESS_GROUP` cũng nằm trong cờ đó: installer chạy qua `subprocess.run` (chờ tới khi xong), không có đường gửi tín hiệu vào nó, nên nhóm tiến trình riêng không gây hại. Nếu bạn thấy nó gây hại, ghi lý do vào bình luận trước khi tách cờ.

## Cách kiểm chứng

Thêm test vào `tests/modloader/test_forge.py`:

1. Giả lập `subprocess.run`, gọi `install_forge` (hoặc hàm chứa lệnh gọi đó) với `sys.platform` giả là `win32`, khẳng định `creationflags` nhận được bằng `CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`.
2. Cùng lệnh gọi đó với platform `linux` và `darwin`, khẳng định `creationflags == 0`.

Tự kiểm bằng cách gỡ bản vá ra: đúng 2 test mới phải đỏ, và đọc thông báo lỗi xác nhận nó đỏ vì đúng lý do. Rồi khôi phục. Dán kết quả cả hai chiều vào bình luận.

Chạy: `pytest tests/modloader/ -q`, `ruff check .`, `mypy src`.

## Tiêu chí xong

- Test mới xanh, gỡ vá thì đỏ đúng chỗ.
- `pytest tests/modloader/ -q` xanh toàn bộ, `ruff`/`mypy` sạch.
- Không đổi hành vi trên Linux/macOS (`creationflags=0`).

## Danh sách file được phép đụng

- `src/nostalgia/modloader/forge.py`
- `tests/modloader/test_forge.py`

Không làm gì ngoài danh sách trên.
