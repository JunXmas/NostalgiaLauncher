import QtQuick

/* Nền kiểu mica từ một ảnh, không cần shader (MultiEffect blur không vẽ được trên GL phần
   mềm, đã thử). Một ảnh 10×10 phóng to lộ lưới ô trên GPU thật; chồng hai lớp 4×4 và 7×7
   lệch tỉ lệ thì lưới của lớp này bị lớp kia xoá. Đặt trong một Item có `clip`. */
Item {
    id: root
    property string source: ""

    anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
    width: parent.width * 0.7
    opacity: base.status === Image.Ready ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: Theme.slow } }

    Image {
        id: base
        anchors.fill: parent
        source: root.source
        sourceSize: Qt.size(4, 4); smooth: true; asynchronous: true
        fillMode: Image.PreserveAspectCrop
        opacity: 0.8
    }
    Image {
        anchors { fill: parent; margins: -60 }
        source: root.source
        sourceSize: Qt.size(7, 7); smooth: true; asynchronous: true
        fillMode: Image.PreserveAspectCrop
        opacity: 0.45
    }
    Rectangle {
        anchors { fill: parent; leftMargin: -root.parent.width * 0.3 }
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Theme.surface }
            GradientStop { position: 0.35; color: "#e6111713" }
            GradientStop { position: 0.7; color: "#80111713" }
            GradientStop { position: 1.0; color: "#26111713" }
        }
    }
}
