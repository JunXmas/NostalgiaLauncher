# Nostalgia 1.2.0rc40 — Cài khi đang chơi, sửa mod một chạm, Legacy Fabric

Bản này tập trung vào những chỗ hay vướng khi chơi modpack.

## Cài nội dung khi đang chơi, xếp hàng nhiều mod

- Không cần thoát Minecraft để cài thêm mod, gói tài nguyên hay shader. Nội dung mới có
  hiệu lực ở lần mở game sau.
- Bấm **Cài** ở nhiều thẻ liền nhau: launcher xếp hàng và cài lần lượt; thẻ đang chờ hiện
  **Trong hàng đợi…**. Phụ thuộc dùng chung (ví dụ Fabric API) chỉ tải một lần.
- Gỡ, tắt hoặc cập nhật nội dung của **đúng bản chơi đang chạy** vẫn phải đợi game tắt.

## Sửa lỗi mod một chạm (miễn phí)

Hộp **Sửa lỗi mod từ log** giờ có thẻ **Sửa ngay** cho những lỗi launcher tự xử lý được:

- mod cần Fabric Loader mới hơn: nâng loader lên bản phù hợp;
- jar tải hỏng, hoặc jar bị log chỉ đích danh làm crash: tắt jar đó (bật lại được);
- thiếu mod phụ thuộc: tìm trên Modrinth và cài.

## Legacy Fabric

- Thêm **Legacy Fabric** vào hộp tạo bản chơi, cho Minecraft 1.13.2 trở xuống.

## Nos Client 0.2.0

Bản chơi tạo từ Optimized tự bật Nos Client. Launcher luôn tải bản Nos mới nhất, nên
không cần cập nhật launcher để nhận bản Nos mới. Bản 0.2.0:

- sửa khoá 30 FPS ở màn chính, HUD mất khi F3+B, full bright mất sau Video Settings;
- thêm màn quản lý waypoint (J), phím sửa HUD (H), minimap đúng tỉ lệ và bản đồ thế
  giới (M).

## Sửa lỗi

- Thư viện CurseForge/Modrinth ngừng hoạt động sau khi để launcher mở vài giờ.
- Kiểm tra cập nhật báo "đã mới nhất" dù đã có bản rc mới hơn.
- Mod có ký tự tab trong metadata (ví dụ BetterGrassify) bị báo nhầm là hỏng.
