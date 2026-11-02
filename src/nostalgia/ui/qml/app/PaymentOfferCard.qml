import QtQuick
import "../" as Legacy

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
            text: Legacy.Tr.phrase("GÓI ") + root.details.planName.toUpperCase()
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
                text: Number(root.details.amount).toLocaleString(Qt.locale(Legacy.Tr.localeName), "f", 0) + Legacy.Tr.phrase("đ")
                font.pixelSize: GlassTheme.fontPrice
                font.weight: Font.DemiBold
                lineHeight: 1
            }
            PaymentText {
                width: parent.width
                text: root.details.lifetime ? Legacy.Tr.phrase("Mua một lần · Ultimate không hết hạn") : root.details.amount < root.details.regularAmount ? Legacy.Tr.format("Ưu đãi cho %1 tháng", [root.details.months]) : Legacy.Tr.format("Tháng sử dụng: %1 · %2", [root.details.months, root.details.planName])
                color: GlassTheme.muted
            }
        }
        Rectangle {
            width: parent.width
            height: 1
            color: GlassTheme.stroke
        }
        PaymentText {
            objectName: "upgradeCreditNote"
            width: parent.width
            visible: root.details.upgradeCredit > 0
            text: Legacy.Tr.format("Đã khấu trừ %1đ từ gói đã mua còn hiệu lực. Thời hạn gói mới bắt đầu khi được kích hoạt.", [Number(root.details.upgradeCredit).toLocaleString(Qt.locale(Legacy.Tr.localeName), "f", 0)])
            color: GlassTheme.accent
        }
        PaymentText {
            width: parent.width
            visible: root.details.eligible === false
            text: Legacy.Tr.phrase("Bạn đang có gói cao hơn hoặc Ultimate. Hãy chọn gói phù hợp; launcher không hạ quyền đang dùng.")
            color: GlassTheme.muted
        }
        PaymentText {
            width: parent.width
            text: root.details.lifetime ? Legacy.Tr.phrase("Gắn với tài khoản Google. Các cập nhật Plus về sau trong thời gian dịch vụ hoạt động.") : Legacy.Tr.format("Gia hạn %1đ/%2 tháng. Không tự động gia hạn.", [Number(root.details.regularAmount).toLocaleString(Qt.locale(Legacy.Tr.localeName), "f", 0), root.details.months])
            color: GlassTheme.muted
        }
        PaymentText {
            width: parent.width
            text: root.details.amount === 0 && root.details.isUpgrade ? Legacy.Tr.phrase("Khoản khấu trừ đủ cho gói mới. Xác nhận để nâng cấp, không cần chuyển khoản thêm.") : root.details.available ? Legacy.Tr.phrase("Quyền Plus được kích hoạt sau khi người quản trị đối chiếu tiền vào Vietcombank và duyệt đơn.") : Legacy.Tr.phrase("Đăng nhập Google để tạo đơn và nhận quyền Plus trên tài khoản của bạn.")
            color: GlassTheme.muted
            font.pixelSize: GlassTheme.fontNote
        }
    }
}
