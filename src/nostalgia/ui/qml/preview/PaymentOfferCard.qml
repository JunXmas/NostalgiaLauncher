import QtQuick

Rectangle {
    id: root
    width: parent.width
    implicitHeight: contents.implicitHeight + 48
    height: implicitHeight
    radius: 20
    color: GlassTheme.alpha(GlassTheme.surface, 0.82)
    border.color: GlassTheme.alpha(GlassTheme.brand, 0.35)
    property var details: paymentBridge.details
    Column {
        id: contents
        x: 24
        y: 24
        width: parent.width - 48
        spacing: 18
        PaymentText {
            text: "GÓI " + root.details.planName.toUpperCase()
            color: GlassTheme.brand
            font.pixelSize: GlassTheme.fontCaption
            font.letterSpacing: 1.3
            font.weight: Font.DemiBold
        }
        Column {
            width: parent.width
            spacing: 6
            PaymentText {
                objectName: "paymentPrice"
                width: parent.width
                text: Number(root.details.amount).toLocaleString(Qt.locale("vi_VN"), "f", 0) + "đ"
                font.pixelSize: GlassTheme.fontPrice
                font.weight: Font.DemiBold
                lineHeight: 1
            }
            PaymentText {
                width: parent.width
                text: root.details.lifetime ? "Mua một lần · Ultimate không hết hạn" : root.details.amount < root.details.regularAmount ? "Ưu đãi cho " + root.details.months + " tháng" : root.details.months + " tháng sử dụng " + root.details.planName
                color: GlassTheme.muted
            }
        }
        Rectangle {
            width: parent.width
            height: 1
            color: GlassTheme.stroke
        }
        PaymentText {
            width: parent.width
            text: root.details.lifetime ? "Gắn với tài khoản Google. Các cập nhật Plus về sau trong thời gian dịch vụ hoạt động." : "Gia hạn " + Number(root.details.regularAmount).toLocaleString(Qt.locale("vi_VN"), "f", 0) + "đ/" + root.details.months + " tháng. Không tự động gia hạn."
            color: GlassTheme.muted
        }
        PaymentText {
            width: parent.width
            text: root.details.available ? "Quyền Plus được ghi nhận sau khi hệ thống xác nhận giao dịch." : "Plus đang được chuẩn bị. Bạn chưa cần chuyển khoản để đăng ký."
            color: GlassTheme.muted
            font.pixelSize: GlassTheme.fontNote
        }
    }
}
