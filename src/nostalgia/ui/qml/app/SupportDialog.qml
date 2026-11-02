import QtQuick
import QtQuick.Controls as Controls
import "../" as Legacy

Controls.Popup {
    id: root
    enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal; easing.type: Easing.OutCubic }
        }
    }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: GlassTheme.quick } }
    objectName: "supportDialog"
    parent: Controls.Overlay.overlay
    width: Math.min(plusPaused ? 680 : receiptMode ? 760 : 1000, parent ? parent.width - 48 : 1000)
    height: Math.min(plusPaused ? 430 : receiptMode ? 660 : details.stage === "pending" ? 840 : ["offer", "unavailable"].indexOf(details.stage) >= 0 ? 560 : 780, parent ? parent.height - 48 : 780)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    padding: 28
    modal: true
    dim: true
    focus: true
    property Item backdrop: null
    property var details: paymentBridge.details
    readonly property bool plusPaused: !plusFeaturesEnabled
    readonly property bool receiptMode: details.stage === "paid"
    readonly property bool compactLayout: height < 650
    property string displayedStage: ""
    signal donateRequested
    closePolicy: Controls.Popup.CloseOnEscape
    onOpened: paymentBridge.setWatching(true)
    onAboutToHide: paymentBridge.setWatching(false)
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
            objectName: "paymentBenefits"
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
                text: Legacy.Tr.phrase("Hồ sơ nổi bật.\nỦng hộ Nostalgia.")
                font.pixelSize: GlassTheme.fontPage
                font.weight: Font.DemiBold
            }
            PaymentText {
                width: parent.width
                text: Legacy.Tr.phrase("Nostalgia+ không khoá tính năng chơi nào. Bạn nhận thứ máy chủ cấp cho tài khoản và giúp Nostalgia tiếp tục phát triển.")
                color: GlassTheme.muted
            }
            Repeater {
                model: [
                    {
                        title: Legacy.Tr.phrase("Cosmetic hồ sơ cao cấp"),
                        description: Legacy.Tr.phrase("Dùng mọi khung và nền hồ sơ, đổi màu hồ sơ. Bạn bè thấy trên hồ sơ của bạn.")
                    },
                    {
                        title: Legacy.Tr.phrase("Huy hiệu Nostalgia+"),
                        description: Legacy.Tr.phrase("Hiện cạnh tên bạn trong danh sách bạn bè và hồ sơ. Ẩn được khi muốn.")
                    },
                    {
                        title: Legacy.Tr.phrase("Dùng thử bản mới sớm"),
                        description: Legacy.Tr.phrase("Tải bản launcher thử nghiệm trước khi phát hành chính thức.")
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
                            font.pixelSize: GlassTheme.fontNote
                            color: GlassTheme.muted
                        }
                    }
                }
            }
        }
    }
    Component {
        id: checkoutPanel
        Item {
            width: (grid.width - (grid.columns - 1) * grid.columnSpacing) / grid.columns
            implicitHeight: cardLoader.item ? cardLoader.item.implicitHeight : 0
            height: implicitHeight
            Loader {
                id: cardLoader
                anchors.fill: parent
                source: root.details.stage === "pending" ? (root.details.qr ? "PaymentQrCard.qml" : "PaymentLinkCard.qml") : "PaymentResultCard.qml"
                onLoaded: {
                    if ("compactLayout" in item)
                        item.compactLayout = Qt.binding(function () {
                            return root.compactLayout;
                        });
                }
            }
        }
    }
    contentItem: Item {
        Item {
            id: header
            width: parent.width
            height: heading.implicitHeight + (root.compactLayout ? 12 : 18)
            Column {
                id: heading
                width: parent.width - 60 - paymentHelp.width - 12
                spacing: root.compactLayout ? 4 : 6
                PaymentText {
                    width: parent.width
                    text: root.plusPaused ? Legacy.Tr.phrase("NOSTALGIA+ · TẠM KHÓA") : root.receiptMode ? Legacy.Tr.phrase("BIÊN NHẬN NOSTALGIA+") : Legacy.Tr.phrase("MIỄN PHÍ VÀ NOSTALGIA+")
                    color: GlassTheme.brand
                    font.pixelSize: GlassTheme.fontCaption
                    font.letterSpacing: 1.5
                }
                PaymentText {
                    width: parent.width
                    text: "Nostalgia+"
                    font.pixelSize: (root.receiptMode ? (root.compactLayout ? 16 : 20) : (root.compactLayout ? 22 : 29)) * GlassTheme.scale
                    font.weight: Font.DemiBold
                }
            }
            GuideButton { id: paymentHelp; topicId: "premium"; anchors.right: parent.right; anchors.rightMargin: 52; anchors.verticalCenter: parent.verticalCenter }
            Button {
                objectName: "paymentClose"
                anchors.right: parent.right
                width: 40
                label: "×"
                quiet: true
                Accessible.name: Legacy.Tr.phrase("Đóng thanh toán")
                onClicked: root.close()
            }
        }
        Item {
            id: footer
            objectName: "paymentFooter"
            readonly property bool stacked: donation.visible && paymentAction.visible && donation.implicitWidth + paymentAction.implicitWidth + 16 > width
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: (stacked ? donation.height + paymentAction.height + 10 : Math.max(donation.height, paymentAction.height, donationNote.visible ? donationNote.implicitHeight : 0)) + 12
            Rectangle {
                width: parent.width
                height: 1
                color: GlassTheme.stroke
            }
            Button {
                id: donation
                objectName: "paymentDonation"
                anchors.bottom: parent.bottom
                anchors.bottomMargin: footer.stacked ? paymentAction.height + 10 : 0
                width: Math.min(implicitWidth, parent.width)
                label: Legacy.Tr.phrase("Ủng hộ tùy tâm  ↗")
                visible: !root.receiptMode
                quiet: true
                onClicked: {
                    root.close();
                    root.donateRequested();
                }
            }
            PaymentText {
                id: donationNote
                objectName: "paymentDonationNote"
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                width: Math.max(0, parent.width - donation.width - 24)
                horizontalAlignment: Text.AlignRight
                text: Legacy.Tr.phrase("Ủng hộ tùy tâm không kích hoạt Nostalgia+.")
                visible: !root.receiptMode && ["offer", "unavailable", "pending"].indexOf(root.details.stage) < 0
                color: GlassTheme.muted
                font.pixelSize: GlassTheme.fontCaption
            }
            Button {
                id: paymentAction
                objectName: root.receiptMode ? "paymentDone" : root.details.stage === "pending" ? "paymentCheck" : "paymentCreate"
                width: Math.min(implicitWidth, parent.width)
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                visible: !root.plusPaused && (root.receiptMode || ["offer", "unavailable", "pending"].indexOf(root.details.stage) >= 0)
                label: root.receiptMode ? Legacy.Tr.phrase("Quay lại launcher") : root.details.stage === "pending" ? (paymentBridge.busy ? Legacy.Tr.phrase("Đang kiểm tra…") : Legacy.Tr.phrase("Kiểm tra thanh toán")) : (paymentBridge.busy ? (root.details.available ? Legacy.Tr.phrase("Đang tạo đơn…") : Legacy.Tr.phrase("Đang tải gói…")) : root.details.error ? Legacy.Tr.phrase("Thử lại") : root.details.available ? (root.details.amount === 0 && root.details.isUpgrade ? Legacy.Tr.phrase("Dùng khoản khấu trừ  →") : root.details.isUpgrade ? Legacy.Tr.phrase("Nâng cấp gói  →") : Legacy.Tr.phrase("Tiếp tục thanh toán  →")) : root.details.stage === "unavailable" ? (socialBridge.signingIn ? Legacy.Tr.phrase("Đang chờ Google…") : Legacy.Tr.phrase("Đăng nhập Google")) : Legacy.Tr.phrase("Tải thông tin gói"))
                primary: true
                clickable: root.receiptMode || !paymentBridge.busy && (root.details.stage === "pending" || root.details.available || !!root.details.error || root.details.stage === "offer" || root.details.stage === "unavailable" && socialBridge.configured && !socialBridge.busy && !socialBridge.signingIn)
                onClicked: {
                    if (root.receiptMode)
                        root.close();
                    else if (root.details.stage === "pending")
                        paymentBridge.checkPayment();
                    else if (root.details.available)
                        paymentBridge.createOrder();
                    else if (root.details.stage === "unavailable")
                        socialBridge.signIn();
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
            anchors.bottomMargin: root.compactLayout ? 12 : 18
            contentHeight: body.implicitHeight + 8
            Column {
                id: body
                width: parent.width - 10
                spacing: root.compactLayout ? 12 : 18
                Rectangle {
                    width: parent.width
                    height: note.implicitHeight + (root.compactLayout ? 16 : 20)
                    radius: 10
                    color: GlassTheme.alpha(root.details.demonstration ? "#e6bb68" : GlassTheme.danger, 0.10)
                    visible: root.details.demonstration || !!root.details.error
                    PaymentText {
                        id: note
                        x: 12
                        y: root.compactLayout ? 8 : 10
                        width: parent.width - 24
                        text: (root.details.demonstration ? Legacy.Tr.phrase("BẢN XEM TRƯỚC · QR mẫu, không chuyển tiền.") : "") + (root.details.error ? (root.details.demonstration ? "\n" : "") + root.details.error : "")
                        color: root.details.error ? GlassTheme.danger : "#e6bb68"
                        font.pixelSize: (root.compactLayout ? 10 : 11) * GlassTheme.scale
                    }
                }
                Button {
                    objectName: "draftPaymentSimulate"
                    visible: typeof draftReviewController !== "undefined" && draftReviewController !== null && root.details.stage === "pending"
                    label: Legacy.Tr.phrase("TEST · Mô phỏng thanh toán thành công")
                    clickable: !paymentBridge.busy
                    onClicked: draftReviewController.simulatePaid()
                }
                PaymentPlans {
                    width: parent.width
                    visible: !root.plusPaused && ["offer", "unavailable"].indexOf(root.details.stage) >= 0
                }
                Grid {
                    id: grid
                    visible: !root.plusPaused && ["offer", "unavailable"].indexOf(root.details.stage) < 0
                    width: parent.width
                    columns: !root.receiptMode && width >= 780 * GlassTheme.scale ? 2 : 1
                    columnSpacing: 32
                    rowSpacing: 24
                    Loader {
                        width: (grid.width - (grid.columns - 1) * grid.columnSpacing) / grid.columns
                        active: grid.visible
                        height: item ? item.implicitHeight : 0
                        sourceComponent: grid.columns === 1 ? checkoutPanel : benefitsPanel
                    }
                    Loader {
                        width: (grid.width - (grid.columns - 1) * grid.columnSpacing) / grid.columns
                        visible: !root.receiptMode
                        active: visible && grid.visible
                        height: visible && item ? item.implicitHeight : 0
                        sourceComponent: grid.columns === 1 ? benefitsPanel : checkoutPanel
                    }
                }
                Glass {
                    objectName: "plusPausedCard"
                    width: parent.width; height: pausedText.implicitHeight + 40; padding: 20
                    visible: root.plusPaused
                    Column {
                        id: pausedText; width: parent.width; spacing: 12
                        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Nostalgia+ đang tạm khóa"); font.pixelSize: GlassTheme.fontTitle; font.weight: Font.DemiBold }
                        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Bản này không bán Nostalgia+. Mọi tính năng chơi vẫn miễn phí như thường."); color: GlassTheme.muted }
                        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Ủng hộ tùy tâm vẫn dùng được, nhưng không kích hoạt Nostalgia+."); color: GlassTheme.muted }
                    }
                }
            }
        }
    }
}
