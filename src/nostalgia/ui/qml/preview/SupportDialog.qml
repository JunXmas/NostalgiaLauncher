import QtQuick
import QtQuick.Controls as Controls
import "../" as Legacy

Controls.Popup {
    id: root
    objectName: "supportDialog"
    parent: Controls.Overlay.overlay
    width: Math.min(1000, parent ? parent.width - 48 : 1000)
    height: Math.min(details.stage === "pending" ? 840 : 780, parent ? parent.height - 48 : 780)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    padding: 28
    modal: true
    dim: true
    focus: true
    property Item backdrop: null
    property var details: paymentBridge.details
    property string displayedStage: ""
    signal donateRequested
    closePolicy: Controls.Popup.CloseOnEscape
    onOpened: paymentBridge.setWatching(true)
    onClosed: paymentBridge.setWatching(false)
    Connections {
        target: paymentBridge
        function onChanged() {
            var stage = paymentBridge.details.stage;
            if (root.displayedStage !== stage) {
                root.displayedStage = stage;
                scroll.contentY = 0;
            }
        }
    }
    background: Glass {
        id: mica
        objectName: "paymentMica"
        padding: 0
        radius: 24
        color: "transparent"
        backdrop: root.backdrop
        backdropRect: {
            if (!root.backdrop || !root.parent)
                return Qt.rect(0, 0, 1, 1);
            var origin = root.parent.mapToItem(root.backdrop, root.x, root.y);
            return Qt.rect(origin.x, origin.y, root.width, root.height);
        }
        frosted: root.opened
        blurOpacity: 0.95
        blurRadius: 64
        finishOpacity: 0.45
        Rectangle {
            anchors.fill: parent
            radius: mica.radius
            color: GlassTheme.alpha(GlassTheme.surface, mica.shaderAvailable ? 0.56 : 0.96)
            border.color: GlassTheme.alpha(GlassTheme.text, 0.14)
        }
    }
    Controls.Overlay.modal: Rectangle {
        color: "#aa080b12"
    }
    Component {
        id: benefitsPanel
        Column {
            width: (grid.width - (grid.columns - 1) * grid.columnSpacing) / grid.columns
            spacing: 20
            Legacy.BlockIcon {
                width: 78
                height: 78
                block: "beacon"
                spinning: false
            }
            PaymentText {
                width: parent.width
                text: "Ít lo lỗi mod.\nNhiều thời gian chơi."
                font.pixelSize: 30 * GlassTheme.scale
                font.weight: Font.DemiBold
            }
            PaymentText {
                width: parent.width
                text: "Plus giúp bạn tìm nguyên nhân và sửa các lỗi mod được hỗ trợ, đồng thời đóng góp cho Nostalgia phát triển."
                color: GlassTheme.muted
            }
            Repeater {
                model: [
                    {
                        title: "Hiểu rõ nguyên nhân",
                        description: "Phân tích xung đột và phụ thuộc theo bộ mod của bạn."
                    },
                    {
                        title: "Sửa với một phương án rõ ràng",
                        description: "Xem mod nào sẽ được thêm, đổi hoặc tắt trước khi áp dụng."
                    },
                    {
                        title: "Có thể quay lại",
                        description: "Sao lưu trước sửa và hoàn tác khi cần."
                    }
                ]
                Row {
                    width: parent.width
                    spacing: 12
                    PaymentText {
                        width: 20
                        text: "✓"
                        color: GlassTheme.brand
                    }
                    Column {
                        width: parent.width - 32
                        spacing: 4
                        PaymentText {
                            width: parent.width
                            text: modelData.title
                            font.weight: Font.DemiBold
                        }
                        PaymentText {
                            width: parent.width
                            text: modelData.description
                            font.pixelSize: 11 * GlassTheme.scale
                            color: GlassTheme.muted
                        }
                    }
                }
            }
            PaymentText {
                width: parent.width
                text: "Dự kiến: Free báo xung đột, Plus hỗ trợ sửa. Không bảo đảm sửa được mọi lỗi."
                color: GlassTheme.muted
                font.pixelSize: 11 * GlassTheme.scale
            }
        }
    }
    Component {
        id: checkoutPanel
        Loader {
            width: (grid.width - (grid.columns - 1) * grid.columnSpacing) / grid.columns
            height: item ? item.height : 0
            source: root.details.stage === "pending" ? "PaymentQrCard.qml" : ["paid", "expired", "cancelled", "verifying"].indexOf(root.details.stage) >= 0 ? "PaymentResultCard.qml" : "PaymentOfferCard.qml"
        }
    }
    contentItem: Item {
        Item {
            id: header
            width: parent.width
            height: heading.implicitHeight + 18
            Column {
                id: heading
                width: parent.width - 60
                spacing: 6
                PaymentText {
                    text: "ỦNG HỘ & PLUS"
                    color: GlassTheme.brand
                    font.pixelSize: 10 * GlassTheme.scale
                    font.letterSpacing: 1.5
                }
                PaymentText {
                    text: "Nostalgia Plus"
                    font.pixelSize: 29 * GlassTheme.scale
                    font.weight: Font.DemiBold
                }
            }
            Button {
                objectName: "paymentClose"
                anchors.right: parent.right
                width: 40
                label: "×"
                quiet: true
                Accessible.name: "Đóng thanh toán"
                onClicked: root.close()
            }
        }
        Item {
            id: footer
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: donation.height + 12
            Rectangle {
                width: parent.width
                height: 1
                color: GlassTheme.stroke
            }
            Button {
                id: donation
                objectName: "paymentDonation"
                anchors.bottom: parent.bottom
                label: "Ủng hộ tùy tâm  ↗"
                quiet: true
                onClicked: {
                    root.close();
                    root.donateRequested();
                }
            }
            PaymentText {
                anchors.right: parent.right
                anchors.verticalCenter: donation.verticalCenter
                width: Math.max(0, parent.width - donation.width - 24)
                horizontalAlignment: Text.AlignRight
                text: "Ủng hộ tùy tâm không kích hoạt Plus."
                visible: ["offer", "unavailable", "pending"].indexOf(root.details.stage) < 0
                color: GlassTheme.muted
                font.pixelSize: 10 * GlassTheme.scale
            }
            Button {
                objectName: root.details.stage === "pending" ? "paymentCheck" : "paymentCreate"
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                visible: ["offer", "unavailable", "pending"].indexOf(root.details.stage) >= 0
                label: root.details.stage === "pending" ? (paymentBridge.busy ? "Đang kiểm tra…" : "Tôi đã chuyển khoản") : (paymentBridge.busy ? (root.details.available ? "Đang tạo đơn…" : "Đang tải gói…") : root.details.error ? "Thử lại" : root.details.available ? "Tiếp tục thanh toán  →" : "Thanh toán sắp mở")
                primary: true
                clickable: !paymentBridge.busy && (root.details.stage === "pending" || root.details.available || !!root.details.error)
                onClicked: {
                    if (root.details.stage === "pending")
                        paymentBridge.checkPayment();
                    else if (root.details.available)
                        paymentBridge.createOrder();
                    else
                        paymentBridge.loadOffer();
                }
            }
        }
        InertialScroll {
            id: scroll
            objectName: "paymentScroll"
            anchors.top: header.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: footer.top
            anchors.bottomMargin: 18
            contentHeight: body.implicitHeight + 8
            Column {
                id: body
                width: parent.width - 10
                spacing: 18
                Rectangle {
                    width: parent.width
                    height: note.implicitHeight + 20
                    radius: 10
                    color: GlassTheme.alpha(root.details.demonstration ? "#e6bb68" : GlassTheme.danger, 0.10)
                    visible: root.details.demonstration || !!root.details.error
                    PaymentText {
                        id: note
                        x: 12
                        y: 10
                        width: parent.width - 24
                        text: (root.details.demonstration ? "BẢN XEM TRƯỚC · QR mẫu, không chuyển tiền." : "") + (root.details.error ? (root.details.demonstration ? "\n" : "") + root.details.error : "")
                        color: root.details.error ? GlassTheme.danger : "#e6bb68"
                        font.pixelSize: 11 * GlassTheme.scale
                    }
                }
                Grid {
                    id: grid
                    width: parent.width
                    columns: width >= 780 * GlassTheme.scale ? 2 : 1
                    columnSpacing: 32
                    rowSpacing: 24
                    Loader {
                        width: (grid.width - (grid.columns - 1) * grid.columnSpacing) / grid.columns
                        height: item ? item.height : 0
                        sourceComponent: grid.columns === 1 ? checkoutPanel : benefitsPanel
                    }
                    Loader {
                        width: (grid.width - (grid.columns - 1) * grid.columnSpacing) / grid.columns
                        height: item ? item.height : 0
                        sourceComponent: grid.columns === 1 ? benefitsPanel : checkoutPanel
                    }
                }
            }
        }
    }
}
