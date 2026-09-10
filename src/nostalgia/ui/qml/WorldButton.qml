import QtQuick

/*
  Nút khối kiểu Minecraft cho MỘT thế giới trong ô CHƠI TIẾP: khung tối, cạnh dưới dày như một
  khối đá, mặt có vệt sáng; rê chuột thì cả khối nhấc lên 2 px và phóng 2 %, ấn thì mặt lún
  xuống (cạnh dưới mỏng đi) — cùng công thức với ActionButton và nút phiên bản ở hộp Tạo bản chơi.
  Chỉ dùng Behavior hữu hạn (không hoạt ảnh lặp) và không có `width: parent.width` trong Row —
  hai thứ từng làm trang chủ ngốn CPU khi đứng yên.
*/
Item {
    id: root
    property string worldName: ""
    property string detail: ""
    property bool clickable: true
    // Ô icon bên trái: ảnh (URL data: của icon server) nếu có, không thì ký tự `glyph`.
    property string iconSource: ""
    property string glyph: "▦"
    readonly property bool iconReady: picture.status === Image.Ready
    signal chosen()

    readonly property int edge: 3
    readonly property int pressDrop: press.pressed && root.clickable ? 3 : 0
    readonly property bool lifted: hover.hovered && root.clickable && !press.pressed
    readonly property int textWidth: root.width - 58

    height: 34

    Item {
        id: block
        width: root.width; height: root.height
        y: root.lifted ? -2 : 0
        scale: root.lifted ? 1.02 : 1
        transformOrigin: Item.Center
        Behavior on y { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }
        Behavior on scale { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }

        Rectangle { anchors.fill: parent; color: "#1e1e1f" }
        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 2 }
            height: parent.height - 4
            color: root.clickable ? "#2e2a25" : "#3b3c3d"
        }
        Rectangle {
            id: face
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 2 }
            anchors.topMargin: 2 + root.pressDrop
            height: parent.height - 4 - root.edge + root.pressDrop
            color: !root.clickable ? "#5a5b5c" : (hover.hovered ? "#5a5247" : "#4a443c")
            Behavior on color { ColorAnimation { duration: Theme.quick } }
            Rectangle {
                anchors { left: parent.left; right: parent.right; top: parent.top }
                height: 2; color: "#33ffffff"
            }
            Row {
                anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
                spacing: 8
                Rectangle {
                    width: 20; height: 20; radius: 4
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.accentSoft; border.color: Theme.accent
                    clip: true
                    Image {
                        id: picture
                        anchors.fill: parent; anchors.margins: 1
                        source: root.iconSource
                        sourceSize: Qt.size(40, 40); smooth: true; mipmap: true; asynchronous: true
                        visible: root.iconReady
                    }
                    Text {
                        anchors.centerIn: parent; visible: !root.iconReady
                        text: root.glyph; color: Theme.accent; font.pixelSize: 11
                    }
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        width: root.textWidth; elide: Text.ElideRight
                        text: root.worldName; color: root.clickable ? "white" : "#b9b9b9"
                        font.pixelSize: 11; font.bold: true
                        style: Text.Raised; styleColor: "#40000000"
                    }
                    Text {
                        width: root.textWidth; elide: Text.ElideRight
                        text: root.detail; color: "#d8cdb8"; font.pixelSize: 9
                    }
                }
            }
        }
    }

    HoverHandler { id: hover; enabled: root.clickable; cursorShape: Qt.PointingHandCursor }
    TapHandler { id: press; enabled: root.clickable; onTapped: { notifier.playUi("select"); root.chosen(); } }
}
