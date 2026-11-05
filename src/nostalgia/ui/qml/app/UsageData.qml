import QtQuick
import "../" as Legacy

WorkspaceDialog {
    id: root
    objectName: "usagePayloadDialog"
    title: Legacy.Tr.phrase("Thống kê tự nguyện và quyền riêng tư")
    description: Legacy.Tr.phrase("Dữ liệu minh họa, không chứa mã thật và không được gửi tới máy chủ.")
    preferredWidth: 740 * GlassTheme.scale
    preferredHeight: 650 * GlassTheme.scale
    Connections { target: usageBridge; function onPayloadRequested() { root.open(); } }
    InertialScroll {
        objectName: "usagePayloadBody"
        anchors.fill: parent
        contentHeight: contents.implicitHeight
        Column {
            id: contents
            width: parent.width
            spacing: 14
            PaymentText { width: parent.width; text: usageBridge.payloadExample; font.family: "monospace"; wrapMode: Text.WrapAnywhere; font.pixelSize: GlassTheme.fontLabel }
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("Mẫu theo schema hiện tại: chỉ sự kiện bản cài hoạt động trong ngày. Không thu sự kiện khởi chạy game, tên tài khoản, token, chat, world, server, log, danh sách mod hay thông tin phần cứng."); color: GlassTheme.muted }
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("Mã được sinh ngẫu nhiên, đổi mỗi ngày UTC và xóa khi tắt. Mỗi mã/ngày được đếm tối đa một lần; đây không phải số người riêng biệt. Cài lại, xóa dữ liệu hoặc bật lại sau khi tắt có thể tạo mã khác."); color: GlassTheme.muted }
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("Mã chống đếm lặp có hạn 24 giờ, dọn hằng giờ. Số liệu tổng hợp giữ 90 ngày. Đăng nhập, cập nhật, tải nội dung và phòng chơi hoạt động độc lập với lựa chọn này."); color: GlassTheme.muted }
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("Khi tắt: hủy lịch và tác vụ chưa gửi, xóa mã ngày, không gửi bù. Request đã rời máy có thể không thu hồi được. Máy chủ và hạ tầng có thể nhìn thấy IP; cấu hình lưu log production chưa được xác minh. Không tuyên bố ẩn danh hoàn toàn."); color: GlassTheme.muted }
            PaymentText { width: parent.width; text: usageBridge.available ? Legacy.Tr.phrase("Nơi nhận: ") + usageBridge.endpoint : Legacy.Tr.phrase("Luồng thống kê tùy chọn chưa được kích hoạt. Launcher không gửi sự kiện tới endpoint thống kê mới."); color: GlassTheme.muted }
        }
    }
    footer: Button { label: Legacy.Tr.phrase("Đóng"); onClicked: root.close() }
}
