import QtQuick

Rectangle {
    id: root
    objectName: "paymentQrCard"
    property var details: paymentBridge.details
    property bool compactLayout: false
    readonly property string timeLeft: Math.floor(details.remaining / 60).toString().padStart(2, "0") + ":" + (details.remaining % 60).toString().padStart(2, "0")
    width: parent.width
    implicitHeight: contents.implicitHeight + (compactLayout ? 32 : 40)
    height: implicitHeight
    radius: 20
    color: GlassTheme.alpha(GlassTheme.surface, 0.82)
    border.color: GlassTheme.stroke
    Column {
        id: contents
        x: root.compactLayout ? 16 : 20
        y: root.compactLayout ? 16 : 20
        width: parent.width - 2 * x
        spacing: 12
        Row {
            width: parent.width
            visible: !root.compactLayout
            PaymentText {
                width: parent.width / 2
                text: root.details.demonstration ? "QR minh họa" : "Quét mã VietQR"
                font.weight: Font.DemiBold
            }
            PaymentText {
                width: parent.width / 2
                horizontalAlignment: Text.AlignRight
                text: "Còn " + root.timeLeft
                color: GlassTheme.muted
                font.pixelSize: 11 * GlassTheme.scale
            }
        }
        Rectangle {
            objectName: "paymentQrFrame"
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(parent.width, Math.max(196, qr.implicitWidth) + 24)
            height: width
            radius: 14
            color: "white"
            clip: true
            Image {
                id: qr
                objectName: "paymentQr"
                anchors.centerIn: parent
                source: root.details.qr
                width: Math.min(implicitWidth, Math.max(0, parent.width - 24))
                height: width
                fillMode: Image.PreserveAspectFit
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
            text: (root.compactLayout ? "Còn " + root.timeLeft + " · " : "") + (root.details.demonstration ? "Mã mẫu, không thanh toán." : "Mở ứng dụng ngân hàng để quét mã.")
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
