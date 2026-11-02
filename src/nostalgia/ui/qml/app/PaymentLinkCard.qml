import QtQuick
import "../" as Legacy

Glass {
    width: parent.width
    padding: 24
    implicitHeight: contents.implicitHeight + 48
    height: implicitHeight
    Column {
        id: contents
        width: parent.width; spacing: 18
        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Đơn thanh toán đã sẵn sàng"); font.pixelSize: GlassTheme.fontTitle; font.weight: Font.DemiBold }
        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Mở trang payOS để xem QR và chuyển khoản. Launcher chỉ kích hoạt Plus khi hệ thống xác nhận giao dịch."); color: GlassTheme.muted }
        Button { width: parent.width; label: Legacy.Tr.phrase("Mở thanh toán payOS  ↗"); primary: true; onClicked: paymentBridge.openCheckout() }
        PaymentCopyLine { label: Legacy.Tr.phrase("Mã đơn"); value: paymentBridge.details.orderId; field: "orderId" }
    }
}
