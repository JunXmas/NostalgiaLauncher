Bản vá cho 1.1.0. Một lỗi, nhưng nó giấu hẳn một nút đi.

## Nút "Dùng" biến mất khi hai tài khoản trùng tên

Nếu bạn đăng nhập một tài khoản Microsoft và một Ely.by **cùng tên**, trang TÀI KHOẢN không
hiện nút **Dùng** ở đâu cả. Lý do: "đang dùng" xưa nay khoá theo tên, nên cả hai hàng đều tự
nhận là hàng đang dùng — mà nút Dùng chỉ hiện ở hàng *không* phải hàng đang dùng.

Bản này đổi danh tính tài khoản sang `account_id` (`kind:uuid`) thay cho tên:

- **Nút Dùng hiện lại**, và bấm nó chạy đúng tài khoản ở hàng đó. Trước đây kể cả vá cho nút
  hiện lên thì bấm Dùng ở hàng Ely.by vẫn chạy game bằng tài khoản Microsoft.
- **Xoá tài khoản chỉ gỡ đúng một hàng.** Trước đây xoá tài khoản Ely.by làm mất luôn vé
  đăng nhập Microsoft trùng tên.
- CLI `--account Ten` gõ tay vẫn dùng được như cũ.

Không cần làm gì khi cập nhật — `accounts.json` cũ đọc được nguyên.
