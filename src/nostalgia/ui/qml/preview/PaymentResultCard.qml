import QtQuick

Rectangle {
    id: root
    property var details: paymentBridge.details
    readonly property bool success: details.stage === "paid"
    readonly property bool verifying: details.stage === "verifying"
    width: parent.width
    height: contents.implicitHeight + 56
    radius: 20
    color: GlassTheme.alpha(GlassTheme.surface, 0.82)
    border.color: GlassTheme.alpha(success ? GlassTheme.brand : GlassTheme.muted, 0.35)
    Column {
        id: contents
        x: 28
        y: 28
        width: parent.width - 56
        spacing: 20
        Rectangle {
            width: 64
            height: 64
            radius: 32
            color: GlassTheme.alpha(root.success ? GlassTheme.brand : GlassTheme.muted, 0.12)
            PaymentText {
                anchors.centerIn: parent
                text: root.success ? "✓" : root.verifying ? "···" : "!"
                font.pixelSize: 28
                color: root.success ? GlassTheme.brand : GlassTheme.muted
            }
        }
        PaymentText {
            objectName: "paymentResultTitle"
            width: parent.width
            text: root.success ? "Cảm ơn bạn đã đồng hành." : root.verifying ? "Đang đối chiếu giao dịch" : root.details.stage === "cancelled" ? "Đơn đã được hủy" : "Mã thanh toán đã hết hạn"
            font.pixelSize: 24 * GlassTheme.scale
            font.weight: Font.DemiBold
        }
        PaymentText {
            width: parent.width
            text: root.success ? "Thanh toán đã được xác nhận. Plus có hiệu lực đến " + root.details.activeUntil + "." : root.verifying ? "Thời gian quét mã đã kết thúc. Hệ thống đang kiểm tra lần cuối; chưa tạo đơn mới trong lúc này." : "Nếu bạn đã chuyển tiền, hãy liên hệ hỗ trợ kèm mã đơn. Đừng chuyển lại khi chưa đối chiếu giao dịch."
            color: GlassTheme.muted
        }
        PaymentCopyLine {
            label: "Mã đơn · dùng khi liên hệ hỗ trợ"
            value: root.details.orderId
            field: "orderId"
        }
        Button {
            objectName: "paymentNewOrder"
            width: parent.width
            visible: !root.success && !root.verifying
            label: "Xem lại gói Plus"
            clickable: !paymentBridge.busy
            onClicked: paymentBridge.newOrder()
        }
        Button {
            objectName: "paymentVerify"
            width: parent.width
            visible: root.verifying
            label: "Kiểm tra giao dịch"
            clickable: !paymentBridge.busy
            onClicked: paymentBridge.checkPayment()
        }
        Button {
            width: parent.width
            label: "Liên hệ hỗ trợ  ↗"
            quiet: true
            visible: !root.success
            onClicked: settingsBridge.openCommunityPage()
        }
    }
}
