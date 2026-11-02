.pragma library

function writing(launcher, contentBusy, installing) {
    if (launcher.gameRunning) return "Đóng Minecraft trước khi thay đổi nội dung.";
    if (launcher.storageBusy) return "Đang xử lý dữ liệu bản chơi. Hãy chờ hoàn tất.";
    if (launcher.busy) return "Launcher đang thực hiện thao tác khác. Hãy chờ hoàn tất.";
    if (contentBusy || installing) return "Đang tải hoặc cài nội dung. Hãy chờ hoàn tất.";
    return "";
}

// Cài THÊM nội dung: không cần đóng game (file mới có hiệu lực ở lần mở sau) và không cần đợi
// lượt cài khác — bấm tiếp là xếp hàng. Chỉ sao lưu/khôi phục mới phải chờ.
function adding(launcher) {
    if (launcher.storageBusy) return "Đang xử lý dữ liệu bản chơi. Hãy chờ hoàn tất.";
    if (launcher.busy && !launcher.gameRunning) return "Launcher đang chuẩn bị bản chơi. Hãy chờ hoàn tất.";
    return "";
}

// Gỡ, tắt, cập nhật nội dung đã cài: chỉ chặn khi đó là bản chơi đang chạy (jar đang được nạp).
function managing(launcher, contentBusy, inRunningGame) {
    if (inRunningGame) return "Đóng Minecraft trước khi gỡ hoặc đổi nội dung của bản chơi đang chạy.";
    if (launcher.storageBusy) return "Đang xử lý dữ liệu bản chơi. Hãy chờ hoàn tất.";
    if (launcher.busy && !launcher.gameRunning) return "Launcher đang thực hiện thao tác khác. Hãy chờ hoàn tất.";
    if (contentBusy) return "Đang tải hoặc cài nội dung. Hãy chờ hoàn tất.";
    return "";
}

function playing(launcher) {
    if (!launcher.activeAccountId) return "Thêm tài khoản Minecraft ở mục Tài khoản để chơi.";
    if (launcher.gameRunning) return "Minecraft đang chạy. Đóng game trước khi mở bản chơi khác.";
    if (launcher.storageBusy) return "Đang xử lý dữ liệu bản chơi. Hãy chờ hoàn tất.";
    if (launcher.busy) return "Launcher đang thực hiện thao tác khác. Hãy chờ hoàn tất.";
    return "";
}

function hosting(launcher, social, host, room, sync, instanceId, share) {
    if (host.details.active || room.active) return "Rời phòng hiện tại trước khi tạo phòng mới.";
    if (!social.signedIn) return "Đăng nhập Google ở mục Bạn bè để tạo phòng và mời bạn.";
    if (!instanceId) return "Tạo hoặc cài một bản chơi rồi chọn ở ô phía trên.";
    var reason = playing(launcher);
    if (reason) return reason;
    if (sync.busy) return "Đang đồng bộ modpack. Hãy chờ hoàn tất hoặc hủy đồng bộ.";
    if (share && !host.modSelection.ready) return "Đang đọc danh sách mod. Nếu có lỗi, chọn lại bản chơi.";
    return "";
}

function joining(launcher, room, sync, instanceId, waitingPack, needsSync) {
    if (room.connectionKind === "failed") return room.canRetryConnection ? "Bấm Thử kết nối lại bên trên trước khi vào world." : "Nhờ host gửi lời mời mới, rồi rời phòng này để vào lại.";
    if (room.locked) return "Host đang khóa phòng. Nhờ host mở khóa để vào world.";
    if (launcher.gameRunning) return "Minecraft đang chạy. Vào Multiplayer để tham gia world, hoặc đóng game để đổi bản chơi.";
    if (!room.worldAvailable) return "Chờ host mở world và bật Open to LAN trong Minecraft.";
    if (room.connectionKind !== "direct") return "Đang kết nối hai máy. Bạn chưa cần mở Minecraft.";
    if (waitingPack) return "Đang lấy thông tin modpack của phòng. Hãy chờ hoàn tất.";
    if (sync.busy) return "Đang đồng bộ modpack. Hãy chờ hoàn tất hoặc hủy đồng bộ.";
    if (needsSync) return "Xem và chọn nội dung modpack bên dưới trước khi vào world.";
    if (!instanceId) return "Chọn bản chơi đã cài khớp Minecraft, loader và mods của host.";
    if (!room.worldReady || room.localPort <= 0) return "Đang kiểm tra đường kết nối vào world. Hãy chờ hoàn tất.";
    return playing(launcher);
}

function installing(launcher, contentBusy, project, picker, success) {
    if (success) return "Phiên bản đã được cài thành công.";
    if (project.details.loading) return "Đang tải thông tin và các phiên bản…";
    if (project.installing) return "Đang cài phiên bản đã chọn. Hãy chờ hoàn tất.";
    var reason = adding(launcher);
    if (reason) return reason;
    if (!picker.isPack && !picker.targets.length) return "Chưa có bản chơi. Tạo bản chơi phù hợp ở phía trên.";
    if (!picker.isPack && !picker.selectedTarget) return "Chọn bản chơi muốn cài vào ở ô Cài vào bản chơi.";
    if (!picker.isPack && !picker.chosen) return "Không có bản phát hành phù hợp với bản chơi này. Hãy thử dự án khác.";
    if (!picker.chosen) return "Chọn bản phát hành phù hợp, hoặc bấm Thử lại nếu tải phiên bản lỗi.";
    if (!picker.canInstall) return "Chọn bản chơi muốn cài vào ở ô Cài vào bản chơi.";
    return "";
}
