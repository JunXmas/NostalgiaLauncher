import QtQuick
import "../" as Legacy
import "ActionReasons.js" as Reasons

/* Khối Chơi đầu trang chủ, luôn hiện: tên bản chơi, ô đổi bản chơi, nút Chơi to nhất trang.
   Như client: mở launcher là bấm Chơi được ngay, không phải lật slide hay vào trang khác. */
Glass {
    id: root
    objectName: "homeHero"
    property var chosen: null
    property var instances: []
    signal playRequested
    signal chooseRequested(string instanceId)
    readonly property bool artworkVisible: settingsBridge.decorativeBackground
    readonly property bool narrow: width < 780
    width: parent.width
    height: Math.max(narrow ? 260 : 280, copy.implicitHeight + padding * 2)
    radius: 26
    padding: narrow ? 24 : 32
    color: GlassTheme.alpha(GlassTheme.selectedSurface, 0.80)
    HomeDiorama {
        id: diorama
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        width: root.narrow ? 170 : Math.min(300, parent.width * 0.30)
        height: Math.min(parent.height, width * 1.10)
        visible: root.artworkVisible
        opacity: root.narrow ? 0.90 : 1
    }
    Column {
        id: copy
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width - (root.artworkVisible ? diorama.width + (root.narrow ? 12 : 32) : 0)
        spacing: 16
        PaymentText {
            width: parent.width
            text: root.chosen ? root.chosen.label : Legacy.Tr.phrase("Một thế giới mới.")
            font.pixelSize: (root.narrow ? 28 : 36) * GlassTheme.scale
            font.weight: Font.DemiBold
            font.letterSpacing: -1
            elide: Text.ElideRight
            wrapMode: Text.NoWrap
        }
        Flow {
            width: parent.width
            spacing: 12
            Button {
                id: playButton
                objectName: "minimalPlay"
                height: 58
                width: Math.max(implicitWidth + 40, 220)
                primary: true
                big: true
                label: bridge.gameRunning ? Legacy.Tr.phrase("Dừng game") : root.chosen ? Legacy.Tr.phrase("Chơi ngay  →") : Legacy.Tr.phrase("Tạo bản chơi  +")
                disabledReason: bridge.gameRunning ? "" : Legacy.Tr.phrase(root.chosen ? Reasons.playing(bridge) : Reasons.writing(bridge, false, false))
                clickable: !disabledReason
                onClicked: root.playRequested()
            }
            Select {
                objectName: "homeInstancePick"
                visible: root.instances.length > 1
                enabled: !bridge.gameRunning
                height: 58
                width: Math.min(260, Math.max(180, copy.width - playButton.width - 12))
                model: root.instances.map(function (i) { return i.label; })
                currentIndex: root.chosen ? root.instances.findIndex(function (i) { return i.instanceId === root.chosen.instanceId; }) : -1
                onActivated: function (index) { root.chooseRequested(root.instances[index].instanceId); }
            }
        }
        Row {
            spacing: 10
            NosChip {
                id: heroNos
                entry: root.chosen || ({})
                visible: !!root.chosen && root.chosen.nosClientSupported === true
            }
            PaymentText {
                anchors.verticalCenter: parent.verticalCenter
                visible: !!root.chosen
                text: root.chosen ? root.chosen.versionId : ""
                color: GlassTheme.muted
                font.pixelSize: GlassTheme.fontBody
            }
        }
        ActionHint { objectName: "homePlayHint"; width: parent.width; reason: playButton.disabledReason }
        PaymentText { objectName: "homeNosHint"; width: parent.width; visible: heroNos.visible; text: heroNos.hint; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote; wrapMode: Text.WordWrap }
    }
}
