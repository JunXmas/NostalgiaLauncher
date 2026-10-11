import QtQuick
import QtQuick.Window

/* Icon dự án: tải từ Modrinth, hỏng hoặc trống thì hiện chữ cái đầu trên nền xanh. */
Rectangle {
    id: root
    property string source: ""
    property string fallbackText: "?"

    width: 44; height: 44; radius: Theme.modern ? 8 : 0
    color: Theme.accentSoft
    clip: true

    Image {
        id: picture
        objectName: "projectIconImage"
        anchors.fill: parent
        source: root.source
        sourceSize: Qt.size(Math.min(256, Math.max(1, Math.ceil(root.width * (Window.window ? Window.window.devicePixelRatio : 1)))), Math.min(256, Math.max(1, Math.ceil(root.height * (Window.window ? Window.window.devicePixelRatio : 1)))))
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        visible: status === Image.Ready
    }
    Text {
        anchors.centerIn: parent
        visible: picture.status !== Image.Ready
        text: root.fallbackText.charAt(0).toUpperCase()
        color: Theme.accent; font.pixelSize: Theme.fontTitle; font.bold: true
    }
}
