import QtQuick

Rectangle {
    id: root
    property var details: paymentBridge.details
    width: parent.width
    height: contents.implicitHeight + 40
    radius: 20
    color: GlassTheme.alpha(GlassTheme.surface, 0.82)
    border.color: GlassTheme.stroke
    Column {
        id: contents
        x: 20
        y: 20
        width: parent.width - 40
        spacing: 12
        Row {
            width: parent.width
            PaymentText {
                width: parent.width / 2
                text: root.details.demonstration ? "QR minh họa" : "Quét mã VietQR"
                font.weight: Font.DemiBold
            }
            PaymentText {
                width: parent.width / 2
                horizontalAlignment: Text.AlignRight
                text: "Còn " + Math.floor(root.details.remaining / 60).toString().padStart(2, "0") + ":" + (root.details.remaining % 60).toString().padStart(2, "0")
                color: GlassTheme.muted
                font.pixelSize: 11 * GlassTheme.scale
            }
        }
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.max(196, qr.implicitWidth) + 24
            height: width
            radius: 14
            color: "white"
            Image {
                id: qr
                objectName: "paymentQr"
                anchors.centerIn: parent
                source: root.details.qr
                width: implicitWidth
                height: implicitHeight
                smooth: false
            }
            PaymentText {
                anchors.centerIn: parent
                width: parent.width - 24
                horizontalAlignment: Text.AlignHCenter
                color: "#333333"
                visible: qr.status === Image.Error
                text: "Không tải được mã QR.\nHãy kiểm tra lại giao dịch."
            }
        }
        PaymentText {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: root.details.demonstration ? "Mã mẫu để xem bố cục, không thanh toán." : "Mở ứng dụng ngân hàng để quét mã."
            color: GlassTheme.muted
            font.pixelSize: 11 * GlassTheme.scale
        }
        PaymentCopyLine {
            label: "Số tiền"
            value: Number(root.details.amount).toLocaleString(Qt.locale("vi_VN"), "f", 0) + "đ"
            field: "amount"
        }
        PaymentCopyLine {
            label: root.details.bank + " · " + root.details.holder
            value: root.details.accountNumber
            field: "accountNumber"
        }
        PaymentCopyLine {
            label: "Nội dung chuyển khoản · giữ nguyên"
            value: root.details.memo
            field: "memo"
        }
        Button {
            objectName: "paymentBrowser"
            width: parent.width
            visible: !!root.details.checkoutUrl && !root.details.demonstration
            label: "Mở trang thanh toán  ↗"
            quiet: true
            onClicked: Qt.openUrlExternally(root.details.checkoutUrl)
        }
    }
}
