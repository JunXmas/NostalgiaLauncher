import QtQuick
import "../" as Legacy

/* Một slide quảng cáo từ feed `promotions.json`: ảnh nền (nếu có), chữ và một nút.
   Loại `server` vào thẳng máy chủ bằng bản chơi đang chọn; loại `link` mở trình duyệt. */
Item {
    id: root
    objectName: "promotionSlide"
    property var slide: ({})
    property var chosen: null
    property int textInset: 32
    readonly property real contentHeight: info.implicitHeight
    readonly property bool server: slide.kind === "server"

    Image {
        anchors.fill: parent
        source: root.slide.image || ""
        visible: !!root.slide.image
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        smooth: true; mipmap: true
    }
    // Tối dần sang trái để chữ đọc được trên mọi ảnh.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#e60b100d" }
            GradientStop { position: 0.55; color: "#800b100d" }
            GradientStop { position: 1.0; color: "#100b100d" }
        }
    }
    Column {
        id: info
        anchors { left: parent.left; leftMargin: root.textInset; verticalCenter: parent.verticalCenter }
        width: Math.min(520, parent.width - root.textInset * 2)
        spacing: 14
        PaymentText {
            text: root.server ? Legacy.Tr.phrase("SERVER GỢI Ý") : Legacy.Tr.phrase("GỢI Ý")
            color: GlassTheme.accent
            font.pixelSize: GlassTheme.fontCaption
            font.letterSpacing: 1.2
        }
        PaymentText {
            objectName: "promotionTitle"
            width: parent.width
            text: root.slide.title || ""
            font.pixelSize: GlassTheme.fontPrice
            font.weight: Font.DemiBold
            font.letterSpacing: -1
        }
        PaymentText {
            width: parent.width
            visible: text.length > 0
            text: root.slide.body || ""
            color: "#dfe6dc"
            font.pixelSize: GlassTheme.fontBody
        }
        PaymentText {
            width: parent.width
            text: root.server ? (root.chosen ? root.slide.target + Legacy.Tr.phrase(" · vào bằng ") + root.chosen.label : Legacy.Tr.phrase("Chọn một bản chơi để vào server."))
                : root.slide.target || ""
            color: "#b8c2b4"
            font.pixelSize: GlassTheme.fontCaption
            elide: Text.ElideRight
        }
        Button {
            objectName: "promotionAction"
            height: 46
            primary: true
            label: (root.slide.button || "") + (root.server ? "  →" : "  ↗")
            clickable: !root.server || (!!root.chosen && !bridge.gameRunning && !bridge.busy && !bridge.storageBusy && bridge.activePlayerName.length > 0)
            onClicked: {
                if (root.server) bridge.playServer(root.chosen.instanceId, root.slide.target);
                else promotionBridge.openLink(root.slide.target);
            }
        }
    }
}
