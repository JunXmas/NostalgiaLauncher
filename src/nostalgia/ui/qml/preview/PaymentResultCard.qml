import QtQuick

Rectangle {
    id: root
    objectName: "paymentResultCard"
    property var details: paymentBridge.details
    property bool compactLayout: false
    readonly property bool success: details.stage === "paid"
    readonly property bool verifying: details.stage === "verifying"
    width: parent.width
    implicitHeight: contents.implicitHeight + (compactLayout ? 40 : 48)
    height: implicitHeight
    radius: 20
    color: GlassTheme.alpha(GlassTheme.surface, 0.82)
    border.color: GlassTheme.alpha(success ? GlassTheme.brand : GlassTheme.muted, 0.35)
    Column {
        id: contents
        x: root.compactLayout ? 20 : 24
        y: root.compactLayout ? 20 : 24
        width: parent.width - 2 * x
        spacing: root.compactLayout ? 14 : 18
        Row {
            width: parent.width
            height: Math.max(mark.height, heading.implicitHeight)
            spacing: 16
            Rectangle {
                id: mark
                width: 48
                height: 48
                radius: 24
                color: GlassTheme.alpha(root.success ? GlassTheme.brand : GlassTheme.muted, 0.12)
                PaymentText {
                    anchors.centerIn: parent
                    text: root.success ? "✓" : root.verifying ? "···" : "!"
                    font.pixelSize: GlassTheme.fontResult
                    color: root.success ? GlassTheme.brand : GlassTheme.muted
                }
            }
            Column {
                id: heading
                width: parent.width - 64
                spacing: 5
                PaymentText {
                    objectName: "paymentResultTitle"
                    width: parent.width
                    text: root.success ? "Thanh toán thành công" : root.verifying ? "Đang đối chiếu giao dịch" : root.details.stage === "cancelled" ? "Đơn đã được hủy" : "Mã thanh toán đã hết hạn"
                    font.pixelSize: (root.compactLayout ? 20 : 24) * GlassTheme.scale
                    font.weight: Font.DemiBold
                }
                PaymentText {
                    visible: root.success
                    text: "Nostalgia Plus · " + (root.details.lifetime ? "Mua đứt" : root.details.months + " tháng")
                    font.pixelSize: (root.compactLayout ? 10 : 13) * GlassTheme.scale
                    color: GlassTheme.muted
                }
            }
        }
        PaymentText {
            width: parent.width
            visible: !root.success || !root.compactLayout
            text: root.success ? "Cảm ơn bạn đã đồng hành cùng Nostalgia." : root.verifying ? "Thời gian quét mã đã kết thúc. Hệ thống đang kiểm tra lần cuối; chưa tạo đơn mới trong lúc này." : "Nếu bạn đã chuyển tiền, hãy liên hệ hỗ trợ kèm mã đơn. Đừng chuyển lại khi chưa đối chiếu giao dịch."
            color: GlassTheme.muted
        }
        Grid {
            width: parent.width
            visible: root.success
            columns: 2
            spacing: 12
            Repeater {
                model: [
                    {
                        label: "Đã thanh toán",
                        value: Number(root.details.amount).toLocaleString(Qt.locale("vi_VN"), "f", 0) + "đ"
                    },
                    {
                        label: "Có hiệu lực đến",
                        value: root.details.activeUntil
                    }
                ]
                Rectangle {
                    width: (parent.width - parent.spacing) / 2
                    height: labels.implicitHeight + (root.compactLayout ? 20 : 28)
                    radius: 12
                    color: GlassTheme.alpha(GlassTheme.background, 0.40)
                    Column {
                        id: labels
                        x: 14
                        y: root.compactLayout ? 10 : 14
                        width: parent.width - 28
                        spacing: 7
                        PaymentText {
                            width: parent.width
                            text: modelData.label
                            font.pixelSize: GlassTheme.fontCaption
                            color: GlassTheme.muted
                        }
                        PaymentText {
                            objectName: index ? "paymentReceiptDate" : "paymentReceiptAmount"
                            width: parent.width
                            text: modelData.value
                            font.pixelSize: (root.compactLayout ? 16 : 20) * GlassTheme.scale
                            font.weight: Font.DemiBold
                        }
                    }
                }
            }
        }
        PaymentCopyLine {
            label: "Mã đơn · lưu để liên hệ hỗ trợ"
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
