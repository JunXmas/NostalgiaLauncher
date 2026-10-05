# Phát hành và tự cập nhật

## Luồng phát hành (chủ dự án làm tay, có cổng duyệt)

1. Tăng phiên bản ở **hai chỗ** và giữ chúng khớp: `pyproject.toml` (`version`) và
   `src/nostalgia/__init__.py` (`__version__`). `tests/test_version_sync.py` gác điều này.
2. Merge vào nhánh chính, rồi tag đúng dạng `vX.Y.Z` và đẩy tag:

   ```sh
   git tag v0.2.0 && git push origin v0.2.0
   ```

3. Workflow `.github/workflows/release.yml` chạy: kiểm tag khớp `__version__`, lint + test,
   rồi trên từng hệ: đóng gói PyInstaller onedir, **chạy thử gói** (`NOSTALGIA_SMOKE_TEST=1`
   nạp QML + cầu nối rồi thoát), và dựng bộ cài:
   - Linux x64 (ubuntu-22.04, glibc 2.35): `.zip` cho bộ tự cập nhật, `.tar.gz`, `.AppImage`
     (appimagetool 1.9.1 ghim sha256), `.deb`, `.rpm` — `packaging/linux/build-packages.sh`.
   - macOS arm64 (macos-14) và x64 (macos-15-intel): `.app` (BUNDLE trong spec) → `.zip` + `.dmg`.
   - Windows x64: `.zip` + `setup.exe` bằng Inno Setup (`packaging/windows/installer.iss`,
     cài vào thư mục người dùng, không cần admin, để bộ tự cập nhật tráo được).
   Cuối cùng ghi `SHA256SUMS` cho mọi file và tạo **GitHub Release dạng DRAFT** với ghi chú
   từ `docs/RELEASE_NOTES.md` (cập nhật file này trước khi tag).
4. Tải gói draft về chạy thử. Ổn thì bấm **Publish release**. Bộ tự cập nhật chỉ nhìn thấy
   bản đã publish (`releases/latest` bỏ qua draft và pre-release). Gói macOS (`.app`) không tự
   tráo — launcher chỉ báo có bản mới và mở trang tải.

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
