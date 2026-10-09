import QtQuick
import QtQuick.Window

Rectangle {
    id: root
    property string clipName: ""
    property bool active: false
    property bool paused: false
    readonly property bool ready: animation.status === Image.Ready
    readonly property bool failed: animation.status === Image.Error
    objectName: "guideMedia"
    color: GlassTheme.background; radius: 14; clip: true
    implicitHeight: width * 0.6
    onClipNameChanged: paused = false
    AnimatedImage {
        id: animation; objectName: "guideAnimation"
        anchors.fill: parent; fillMode: Image.PreserveAspectFit
        source: root.active && root.clipName ? "../assets/guides/" + root.clipName + ".gif" : ""
        asynchronous: true; cache: false
        playing: root.active && !root.paused && !GlassTheme.reducedMotion && Window.window && Window.window.visible && Qt.application.state === Qt.ApplicationActive
        Accessible.role: Accessible.Graphic
        Accessible.name: "Minh họa thao tác trên launcher; dữ liệu trong ảnh là ví dụ."
    }
    PaymentText {
        anchors.centerIn: parent; width: parent.width - 36; horizontalAlignment: Text.AlignHCenter
        visible: !root.ready
        text: root.failed ? "Chưa tải được ảnh minh họa. Bạn vẫn có thể làm theo các bước bên dưới." : "Đang tải minh họa…"
        color: GlassTheme.muted
    }
}
