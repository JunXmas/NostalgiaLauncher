import QtQuick

Glass {
    id: root
    objectName: "homeHero"
    property var chosen: null
    signal playRequested
    signal libraryRequested
    readonly property bool artworkVisible: settingsBridge.decorativeBackground
    readonly property bool narrow: width < 780
    width: parent.width
    height: Math.max(narrow ? 340 : 370, copy.implicitHeight + padding * 2)
    radius: 26
    padding: narrow ? 24 : 32
    color: GlassTheme.alpha(GlassTheme.selectedSurface, 0.80)
    HomeDiorama {
        id: diorama
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        width: root.narrow ? 190 : Math.min(420, parent.width * 0.42)
        height: Math.min(parent.height, width * 1.10)
        visible: root.artworkVisible
        opacity: root.narrow ? 0.90 : 1
    }
    Column {
        id: copy
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width - (root.artworkVisible ? diorama.width + (root.narrow ? 12 : 32) : 0)
        spacing: 18
        Row {
            width: parent.width
            spacing: 8
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 6
                height: 6
                radius: 3
                color: GlassTheme.accent
            }
            PaymentText {
                width: parent.width - 14
                text: root.chosen ? "THẾ GIỚI CỦA BẠN VẪN Ở ĐÂY" : "MỘT KHỞI ĐẦU MỚI"
                color: GlassTheme.accent
                font.pixelSize: GlassTheme.fontCaption
                font.letterSpacing: 1.2
            }
        }
        PaymentText {
            width: parent.width
            text: root.chosen ? "Về với thế giới\ncủa bạn." : "Một thế giới mới.\nMột cuộc phiêu lưu."
            font.pixelSize: (root.narrow ? 28 : 38) * GlassTheme.scale
            font.weight: Font.DemiBold
            font.letterSpacing: -1
            lineHeight: 1.12
        }
        PaymentText {
            width: parent.width
            text: root.chosen ? root.chosen.label + " · " + root.chosen.versionId : "Từ một góc nhỏ, đến những điều chưa khám phá."
            color: GlassTheme.muted
            font.pixelSize: GlassTheme.fontBody
        }
        Flow {
            width: parent.width
            spacing: 10
            Button {
                objectName: "minimalPlay"
                height: 46
                primary: true
                label: bridge.gameRunning ? "Dừng game" : root.chosen ? "Chơi ngay  →" : "Tạo bản chơi  +"
                clickable: bridge.gameRunning || (!bridge.busy && !bridge.storageBusy && (!root.chosen || !!bridge.activePlayerName))
                onClicked: root.playRequested()
            }
            Button {
                height: 46
                label: "Khám phá modpack"
                quiet: true
                onClicked: root.libraryRequested()
            }
        }
    }
}
