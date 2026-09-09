import QtQuick

/* Mặt nhân vật cắt từ skin 64x64: vùng (8,8) 8x8 + lớp mũ (40,8). Không cần dịch vụ ngoài. */
Item {
    id: root
    property string source: ""
    property int size: 32
    width: size; height: size

    Image {
        anchors.fill: parent
        source: root.source; sourceClipRect: Qt.rect(8, 8, 8, 8)
        smooth: false; cache: true
    }
    Image {
        anchors.fill: parent; anchors.margins: -root.size / 16  // lớp mũ nhô ra một chút như trong game
        source: root.source; sourceClipRect: Qt.rect(40, 8, 8, 8)
        smooth: false; cache: true
    }
}
