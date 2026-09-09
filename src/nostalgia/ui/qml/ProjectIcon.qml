import QtQuick

/* Icon dự án: tải từ Modrinth, hỏng hoặc trống thì hiện chữ cái đầu trên nền xanh. */
Rectangle {
    id: root
    property string source: ""
    property string fallbackText: "?"

    width: 44; height: 44; radius: 10
    color: Theme.accentSoft
    clip: true

    Image {
        id: picture
        anchors.fill: parent
        source: root.source
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        visible: status === Image.Ready
    }
    Text {
        anchors.centerIn: parent
        visible: picture.status !== Image.Ready
        text: root.fallbackText.charAt(0).toUpperCase()
        color: Theme.accent; font.pixelSize: 18; font.bold: true
    }
}
