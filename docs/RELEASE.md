# Phát hành và tự cập nhật

## Luồng phát hành (chủ dự án làm tay, có cổng duyệt)

1. Tăng phiên bản ở **hai chỗ** và giữ chúng khớp: `pyproject.toml` (`version`) và
   `src/nostalgia/__init__.py` (`__version__`). `tests/test_version_sync.py` gác điều này.
2. Merge vào nhánh chính, rồi tag đúng dạng `vX.Y.Z` và đẩy tag:

   ```sh
   git tag v0.2.0 && git push origin v0.2.0
   ```

3. Workflow `.github/workflows/release.yml` chạy: kiểm tag khớp `__version__`, lint + test,
   đóng gói PyInstaller onedir cho Linux và Windows, nén thành
   `nostalgia-<ver>-<os>-x64.zip`, ghi `SHA256SUMS`, và tạo **GitHub Release dạng DRAFT**.
4. Tải gói draft về chạy thử. Ổn thì bấm **Publish release**. Bộ tự cập nhật chỉ nhìn thấy
   bản đã publish (`releases/latest` bỏ qua draft và pre-release).

Gom nhiều thay đổi vào một bản — đừng ra bản dồn dập để người dùng kịp test.

## Bộ tự cập nhật trong launcher

- Lúc mở launcher (sau 3 giây, tắt được ở CÀI ĐẶT → CẬP NHẬT) hoặc bấm "Kiểm tra bản mới":
  hỏi `releases/latest`, so phiên bản (semver viết tay, bản beta xếp dưới bản chính).
- Có bản mới → toast + mục CẬP NHẬT hiện ghi chú và nút Tải về. Gói được tải qua HTTPS
  (theo 302 của GitHub sang CDN, tối đa 5 bước, đích vẫn phải là https), băm sha256 ngay khi
  tải, đối chiếu với `SHA256SUMS` của chính bản đó. **Không có SHA256SUMS hoặc sai băm → từ
  chối, xoá file dở.** Gói bung vào `<data_dir>/updates/<ver>/`, mỗi entry zip đi qua
  `resolve_within` (chặn `../`).
- Áp bản mới chỉ khi launcher là **gói đóng sẵn** (`sys.frozen`): launcher viết script tráo
  thư mục (`apply-update.sh` / `.cmd`), chạy tách rời, rồi thoát; script chờ tiến trình cũ
  tắt, đổi thư mục cài thành `.old`, chép bản mới vào, xoá bản cũ, mở launcher mới. Chép hỏng
  thì trả lại bản cũ. Chạy từ mã nguồn (`uv run nostalgia-ui`) thì launcher chỉ báo và mở
  trang release — cập nhật bằng `git pull` + `uv sync`.

## Đóng gói thử trên máy

```sh
uv sync --extra ui --group build
uv run pyinstaller --noconfirm packaging/nostalgia-ui.spec
QT_QPA_PLATFORM=offscreen dist/nostalgia-ui/nostalgia-ui   # phải mở được, không traceback
```
