import QtQuick
import "../" as Legacy

Column {
    width: parent.width
    spacing: 12
    visible: typeof serviceConfiguration !== "undefined"
    PaymentText { width: parent.width; font.weight: Font.DemiBold; text: Legacy.Tr.phrase("Tài khoản Nostalgia") }
    PaymentText { objectName: "serviceStatus"; width: parent.width; text: typeof socialBridge !== "undefined" && socialBridge.configured ? Legacy.Tr.phrase("Google đã được tích hợp. Đăng nhập trong mục Bạn bè hoặc màn hình chào.") : Legacy.Tr.phrase("Đăng nhập Google chưa khả dụng trong bản thử này. Chờ bản cập nhật từ Nostalgia."); color: GlassTheme.muted }
    PaymentText { width: parent.width; visible: typeof plusFeaturesEnabled !== "undefined" && !plusFeaturesEnabled; text: Legacy.Tr.phrase("Bản này không bán Nostalgia+. Mọi tính năng chơi vẫn miễn phí như thường."); color: GlassTheme.muted }
}
