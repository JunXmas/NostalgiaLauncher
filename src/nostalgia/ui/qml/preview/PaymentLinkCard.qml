import QtQuick

Glass {
    width: parent.width
    padding: 24
    implicitHeight: contents.implicitHeight + 48
    height: implicitHeight
    Column {
        id: contents
        width: parent.width; spacing: 18
        PaymentText { width: parent.width; text: "Đơn thanh toán đã sẵn sàng"; font.pixelSize: GlassTheme.fontTitle; font.weight: Font.DemiBold }
        PaymentText { width: parent.width; text: "Mở trang payOS để xem QR và chuyển khoản. Launcher chỉ kích hoạt Plus khi hệ thống xác nhận giao dịch."; color: GlassTheme.muted }
        Button { width: parent.width; label: "Mở thanh toán payOS  ↗"; primary: true; onClicked: paymentBridge.openCheckout() }
        PaymentCopyLine { label: "Mã đơn"; value: paymentBridge.details.orderId; field: "orderId" }
    }
}
