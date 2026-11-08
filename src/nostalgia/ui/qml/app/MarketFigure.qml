import QtQuick
import "../" as Legacy
Item {
    id: root
    property string skinSource: ""
    property bool slim: false
    property string digest: ""
    property real yaw: 25
    implicitHeight: 390
    function schedule() { refresh.restart(); }
    onSkinSourceChanged: schedule()
    onSlimChanged: schedule()
    onDigestChanged: schedule()
    onYawChanged: schedule()
    Component.onCompleted: schedule()
    Timer { id: refresh; interval: 60; onTriggered: marketPreviews.show(root.skinSource, root.slim, root.digest, root.yaw) }
    Rectangle { anchors.fill: parent; radius: 20; color: Legacy.Theme.mix(GlassTheme.raised, GlassTheme.accent, 0.10); border.color: GlassTheme.stroke }
    Image { id: figure; objectName: "marketPlayerPreview"; anchors.fill: parent; anchors.margins: 12; source: marketPreviews.source; asynchronous: true; cache: false; fillMode: Image.PreserveAspectFit }
    MouseArea {
        anchors.fill: parent
        property real lastX: 0
        onPressed: function(mouse) { root.forceActiveFocus(); lastX = mouse.x; }
        onPositionChanged: function(mouse) { if (pressed) { root.yaw += (mouse.x-lastX)*0.8; lastX=mouse.x; } }
    }
    activeFocusOnTab: true
    Keys.onLeftPressed: yaw -= 15
    Keys.onRightPressed: yaw += 15
    PaymentText { anchors.bottom: parent.bottom; anchors.bottomMargin: 12; anchors.horizontalCenter: parent.horizontalCenter; text: marketPreviews.busy ? Legacy.Tr.phrase("Đang tải preview…") : Legacy.Tr.phrase("Kéo để xoay nhân vật"); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
}
