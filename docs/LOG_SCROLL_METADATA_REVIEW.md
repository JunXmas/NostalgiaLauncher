# Nhật ký và cảnh báo metadata

Bản sửa chưa phát hành trong installer rc13.

## Cuộn nhật ký

Log ListView dừng ở biên, không bật overshoot. Bộ điều khiển quán tính tính biên
bằng originY của ListView; origin thay đổi khi dòng cũ bị xóa hoặc chiều cao dòng
được ước lượng lại. Điểm đến được dịch theo origin, không kéo về tọa độ 0 giả định.

Cuộn lên tắt bám đuôi trước khi animation bắt đầu. Thêm dòng và giữ tối đa 5.000
dòng không tự kéo người đang đọc về cuối. Việc bám đuôi được dồn một lần ở nhịp
layout sau và không tranh vị trí với kéo/cuộn quán tính. Reduced motion vẫn được giữ.

## Độ chắc chắn

Metadata sinh cảnh báo; không chứng minh instance không chạy được. UI ghi nguồn
metadata/log và mức độ. Runtime/mixin chưa đủ bằng chứng chọn phiên bản vẫn là
cảnh báo. Mẫu lỗi dependency rõ ràng trong log mới được ghi là lỗi.

Fabric environment=server không tham gia inventory client. Alias không tạo lỗi
trùng mod độc lập và không ghi đè mod ID thực. JAR lồng là các ứng viên loader,
không tự coi toàn bộ JAR cha là mod trùng. Đọc Forge/NeoForge JarJar để nhận diện
thư viện mod được đóng gói; thư viện Java thường không có metadata mod được bỏ qua.
Lựa chọn phiên bản lồng chưa giải được không được đoán thành lỗi chắc chắn.
NeoForge 1.20.1 đọc mods.toml và dependency Forge 47.x theo định dạng cũ.

Debug/crash cũ hơn latest.log quá hai giây được loại để tránh tái dùng lỗi của
lần chạy trước. Đây là kiểm tra freshness, không phải máy giải lỗi cho mọi crash.
Không upload toàn bộ log, token, đường dẫn hoặc stack trace: chỉ gửi bằng chứng
cấu trúc thuộc mẫu hỗ trợ.

## Sửa mod

UI chỉ lập phương án khi có diagnostic log. Payload mới mang repair_policy
log-confirmed; backend chỉ đề xuất thay đổi từ bằng chứng này, vẫn kiểm tra các
constraint metadata của bản được tải. Không tắt JAR cha để thay thư viện lồng,
không tắt mod cung cấp alias khi chưa xác minh bản thay thế.

Giữ quyền Plus, proof/session, hash scan, hash tải, backup và hoàn tác hiện có.
Khi kiểm lại, các cảnh báo cũ không liên quan không chặn một phương án dựa trên
log; cảnh báo mới hoặc tác động vào mod/dependency được sửa vẫn chặn áp dụng.
Payload cũ tiếp tục được hỗ trợ để không phá các client đã phát hành.

## Xác minh

- Kiểm thử core quét/sửa: JAR thật do fixture tạo, environment, alias, Fabric
  nested, Forge JarJar, NeoForge legacy, freshness, log constraints, stage/undo.
- Qt/OpenGL: nhật ký 5.000 dòng, kéo quá biên, wheel đảo chiều, model cắt dòng,
  đọc ngược trong lúc dòng mới thêm; reduced motion và menu chọn phiên bản.
- Backend: log-confirmed, alias/nested parent guard, constraint/catalog match,
  session/quyền Plus, scan hash và authorize một lần.

Đây là fixture tổng hợp; chưa tái chạy chính modpack của người báo lỗi và không
khẳng định có thể phát hiện mọi xung đột hoặc bảo đảm mọi instance đều chạy.
