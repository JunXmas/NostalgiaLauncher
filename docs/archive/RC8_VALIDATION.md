# rc8 — Ultimate TEST draft validation

Client: nhánh `preview/glass-review`. Backend private giữ commit
`bb519087aed8c52ed627d6b25f4fd143c5db08bb` trên `preview/google-plus-rc2`.
Không merge main, không publish, không deploy backend và không thu tiền thật.

## Phạm vi review

- Entry review riêng được chọn lúc build cho duy nhất tag `v1.2.0rc8`.
  Mỗi lần chạy mặc định Ultimate TEST; dữ liệu cosmetic test lưu riêng.
- Build thường mặc định `release`, loại `nostalgia_draft` khỏi PyInstaller.
  Wheel chỉ gồm `src/nostalgia`. Không có biến môi trường runtime mở Premium.
- Server chạy local qua manager thật. Review chỉ thay authorization adapter.
- Planner local thận trọng: trùng ID/sai loader/xung đột; không giả lập việc tải
  dependency chưa xác minh. Transaction core vẫn kiểm hash, quét stage, chặn game
  đang chạy, sao lưu và hỗ trợ hoàn tác.
- Đồng bộ local đi qua snapshot/manifest/hash/install thật, tạo bản chơi mới;
  không đổi trạng thái relay hoặc giả gửi lời mời cho người dùng online.
- Thanh toán không có bank account, VietQR trả tiền hay checkout URL.
  Nút xác nhận của người dùng giữ pending; chỉ công cụ TEST riêng mô phỏng paid.
- Google/bạn bè thật cần backend; mã review không viết entitlement từ xa.

## Kết quả kiểm tra

- Full client: **1491 passed, 7 skipped, 1 deselected**, 330,48 giây. Test mạng/game thật vẫn loại/bỏ qua theo cấu hình kho.
- Native OpenGL: **24 passed** cho cosmetic, confirmation, server UI, menu và cuộn; sau thay đổi cuối, **2 passed** cho toàn bộ trang draft, đổi gói, thanh toán mô phỏng và đồng bộ qua nút bấm thật. Không có QML warning trong lượt kiểm tra toàn trang/ảnh capture.
- Ruff check, format check (583 files), mypy (541 source/test files), uv locked sync/build và git diff check qua.
- PyInstaller production và review đều build/smoke thành công trên Linux local. Smoke review xác nhận Ultimate và quyền server.
- Kiểm tra PYZ thực tế: production không có module nostalgia_draft; review có entry riêng. Wheel thường cũng không có adapter review.
- GitHub Actions Release kiểm lại toàn bộ trước khi build Windows x64, Linux x64, macOS arm64/x64. Mỗi gói chạy smoke trên runner của hệ điều hành đó, kiểm flavor và kèm SHA256SUMS cho bộ cài/hướng dẫn. Theo dõi kết quả CI của tag v1.2.0rc8; không xem native smoke là thử Minecraft/LAN thật.
- Ảnh QA để ngoài release. Chỉ đính kèm bộ cài, checksum và tài liệu kiểm thử.

## Giới hạn

Chưa có URL account/relay hoặc credential deploy trong workspace. Google thật,
keyring Windows/macOS, game/Forge/LAN nhiều máy và giao dịch ngân hàng chưa được
xác minh. OpenGL QA dùng Xorg/Mesa llvmpipe, không phải benchmark FPS trên GPU.
