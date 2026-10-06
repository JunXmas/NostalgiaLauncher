import QtQuick
import "../" as Legacy

Item {
    id: root
    objectName: "interfaceChooser"
    implicitWidth: 1440
    implicitHeight: 900
    property string selectedStyle: settingsBridge.interfaceStyle
    readonly property bool compact: height < 700
    readonly property bool switchBusy: bridge.busy || accountBridge.busy || contentBridge.busy || storageBridge.busy || importBridge.busy
    Component.onCompleted: {
        GlassTheme.preferences = settingsBridge;
        GlassTheme.backdrop = ambient;
        Legacy.Theme.preferences = settingsBridge;
        Legacy.Theme.page = 0;
    }
    Ambient {
        id: ambient
        anchors.fill: parent
    }
    Row {
        x: 40
        y: 28
        spacing: 12
        Image {
            width: 30
            height: 30
            source: "../assets/logo.png"
            mipmap: true
        }
        PaymentText {
            anchors.verticalCenter: parent.verticalCenter
            text: "Nostalgia"
            font.pixelSize: 19
            font.weight: Font.DemiBold
        }
    }
    InertialScroll {
        id: scroll
        objectName: "interfaceChoiceScroll"
        anchors.horizontalCenter: parent.horizontalCenter
        y: root.compact ? 78 : 126
        width: Math.min(1120, parent.width - 80)
        height: footer.y - y - 24
        contentHeight: contents.implicitHeight + 8
        Column {
            id: contents
            width: parent.width - 10
            spacing: root.compact ? 16 : 32
            Column {
                width: parent.width
                spacing: 8
                PaymentText {
                    width: parent.width
                    text: "Chọn không gian của bạn."
                    font.pixelSize: (root.compact ? 22 : 36) * GlassTheme.scale
                    font.weight: Font.DemiBold
                }
                PaymentText {
                    width: parent.width
                    text: "Hai diện mạo Nostalgia. Bạn thích cách nào?"
                    color: GlassTheme.muted
                    font.pixelSize: (root.compact ? 12 : 14) * GlassTheme.scale
                }
            }
            Grid {
                id: choices
                width: parent.width
                columns: width >= 760 ? 2 : 1
                spacing: 24
                readonly property real tileWidth: (width - (columns - 1) * spacing) / columns
                readonly property real tileHeight: Math.max(classic.implicitHeight, modern.implicitHeight)
                InterfaceChoiceCard {
                    id: classic
                    objectName: "interfaceChoice-classic"
                    width: choices.tileWidth
                    height: choices.tileHeight
                    style: "classic"
                    title: "Giao diện cũ"
                    description: "Bố cục quen thuộc, nét Minecraft cổ điển."
                    previewSource: "../assets/interface/classic.png"
                    compact: root.compact
                    selected: root.selectedStyle === style
                    onChosen: function (style) {
                        root.selectedStyle = style;
                    }
                }
                InterfaceChoiceCard {
                    id: modern
                    objectName: "interfaceChoice-modern"
                    width: choices.tileWidth
                    height: choices.tileHeight
                    style: "modern"
                    title: "Giao diện mới"
                    description: "Bố cục thoáng, kính mờ nhẹ và màu Nostalgia."
                    previewSource: "../assets/interface/modern.png"
                    compact: root.compact
                    selected: root.selectedStyle === style
                    onChosen: function (style) {
                        root.selectedStyle = style;
                    }
                }
            }
        }
    }
    Item {
        id: footer
        anchors.horizontalCenter: parent.horizontalCenter
        width: scroll.width
        height: Math.max(continueButton.height, footerNote.implicitHeight) + 24
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
        Rectangle {
            width: parent.width
            height: 1
            color: GlassTheme.stroke
        }
        Column {
            id: footerNote
            y: 20
            width: parent.width - continueButton.width - 28
            spacing: 4
            PaymentText {
                width: parent.width
                text: settingsBridge.interfaceSelectionError || (root.switchBusy ? "Đợi tác vụ hiện tại hoàn tất để đổi giao diện." : "Có thể đổi trong Cài đặt → Giao diện.")
                font.pixelSize: 12 * GlassTheme.scale
                color: settingsBridge.interfaceSelectionError ? GlassTheme.danger : GlassTheme.muted
            }
            Button {
                objectName: "interfaceChoiceCancel"
                visible: !!settingsBridge.interfaceStyle
                label: "← Giữ giao diện hiện tại"
                quiet: true
                onClicked: interfaceSetup.cancel()
            }
        }
        Button {
            id: continueButton
            objectName: "interfaceChoiceContinue"
            anchors.right: parent.right
            y: 20
            label: "Tiếp tục  →"
            primary: true
            clickable: !!root.selectedStyle && !root.switchBusy
            onClicked: interfaceSetup.choose(root.selectedStyle)
        }
    }
}
