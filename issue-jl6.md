Cùng nhóm lỗi "cửa sổ đen bật lên trên Windows", nhưng ở đường tự cập nhật chứ không phải chạy game.

## Việc cần làm

`src/nostalgia/update/apply.py:91` chạy script tráo bản bằng:

```python
detached = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
subprocess.Popen(["cmd.exe", "/c", str(script_path)], creationflags=detached, close_fds=True)
```

`DETACHED_PROCESS` chỉ nói "đừng kế thừa console của cha", không nói "đừng có console". `cmd.exe` là app console: chạy không console thì nó tự gọi `AllocConsole`, và Windows dựng một cửa sổ mới. Người dùng cập nhật launcher sẽ thấy cửa sổ CMD nhấp nháy.

Thêm `CREATE_NO_WINDOW` vào là vô ích — tài liệu Win32 nói rõ cờ này **bị bỏ qua** khi dùng chung với `DETACHED_PROCESS` hoặc `CREATE_NEW_CONSOLE`. Phải thay, không phải thêm.

Hướng đề xuất: `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`, bỏ `DETACHED_PROCESS`.

**Trước khi sửa, tự kiểm lại giả định quan trọng nhất của bản vá này:** script phải sống sót sau khi launcher thoát, nếu không thì cập nhật hỏng nặng hơn cả cửa sổ nhấp nháy. Windows không giết tiến trình con khi cha chết (không có process tree kill mặc định), nên bỏ `DETACHED_PROCESS` không làm script chết theo. Đọc lại code và xác nhận điều này đúng với cách `apply.py` gọi; nếu bạn tìm được lý do nó KHÔNG đúng, **dừng lại, ghi vào bình luận, đừng sửa** — đây là đường cập nhật, sai là người dùng mất launcher.

Thêm `stdin/stdout/stderr=subprocess.DEVNULL` nếu cần để script không dính stdio của launcher đang thoát.

Tách phần chọn cờ thành hàm thuần để kiểm được từ máy Linux, theo đúng lối `resolve_creation_flags` ở `src/nostalgia/launch/game_process.py:60`.

## Cách kiểm chứng

Trong `tests/update/test_update_apply.py` (hoặc file test tương ứng đang có):

1. Test hàm thuần chọn cờ: `win32` ra `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`, và khẳng định **không** chứa `DETACHED_PROCESS` (0x00000008) — đây mới là test gác đúng lỗi.
2. `linux`/`darwin` ra 0.
3. Giả lập `Popen`, khẳng định `launch_swap_script` truyền đúng cờ đó khi `windows=True`.
4. Giữ nguyên các test hiện có cho nhánh POSIX (`/bin/sh`, `start_new_session=True`) — không được đỏ.

Gỡ vá ra, xác nhận đúng test mới đỏ và đỏ vì đúng lý do, rồi khôi phục. Dán cả hai chiều vào bình luận.

Chạy: `pytest tests/update/ -q`, `ruff check .`, `mypy src`.

## Tiêu chí xong

- Test mới xanh, gỡ vá thì đỏ đúng chỗ.
- Nhánh POSIX không đổi hành vi một chút nào.
- Trong bình luận có một đoạn ngắn xác nhận (hoặc bác bỏ) giả định "script sống sót sau khi launcher thoát", kèm căn cứ.

## Danh sách file được phép đụng

- `src/nostalgia/update/apply.py`
- `tests/update/test_update_apply.py`

Không làm gì ngoài danh sách trên.
