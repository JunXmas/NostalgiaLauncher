import QtQuick

/* Nền kiểu mica từ một ảnh, không cần shader (MultiEffect blur không vẽ được trên GL phần
   mềm, đã thử). Hai lớp 16×16 và 28×28 lệch tỉ lệ chồng nhau: đủ mờ để chữ đọc rõ, nhưng vẫn
   nhận ra hình icon (4×4 chỉ còn một mảng màu; 32×32 trở lên lộ lưới ô trên GPU thật — đã so
   ba mức bằng mắt). Đặt trong một Item có `clip`. */
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
        sourceSize: Qt.size(16, 16); smooth: true; asynchronous: true
        fillMode: Image.PreserveAspectCrop
        opacity: 0.8
    }
    Image {
        anchors { fill: parent; margins: -30 }
        source: root.source
        sourceSize: Qt.size(28, 28); smooth: true; asynchronous: true
        fillMode: Image.PreserveAspectCrop
        opacity: 0.4
    }
    Rectangle {
        anchors { fill: parent; leftMargin: -root.parent.width * 0.3 }
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Theme.surface }
            GradientStop { position: 0.35; color: "#e6111713" }
            GradientStop { position: 0.7; color: "#66111713" }
            GradientStop { position: 1.0; color: "#1a111713" }
        }
    }
}
