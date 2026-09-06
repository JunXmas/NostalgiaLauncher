import QtQuick

/* Thẻ một bản chơi: ô ảnh có nút chạy, rồi tên và thông tin thật bên dưới. */
Rectangle {
    id: root
    property string label: ""
    property string versionId: ""
    property bool playable: true
    property bool removable: false
    property bool confirmingRemove: false
    signal playRequested()
    signal removeRequested()

    // Suy loader từ mã phiên bản: "fabric-loader-…", "1.20.1-forge-…", "neoforge-…".
    readonly property string loaderLabel: versionId.indexOf("fabric") >= 0 ? "Fabric"
                                        : versionId.indexOf("neoforge") >= 0 ? "NeoForge"
                                        : versionId.indexOf("forge") >= 0 ? "Forge" : "Vanilla"

    implicitWidth: 230
    implicitHeight: 168
    radius: Theme.radius
    color: hover.hovered ? Theme.surfaceHigh : Theme.surface
    border.color: hover.hovered ? Theme.accent : Theme.border
    border.width: 1
    opacity: 0
    scale: 0.97

    Behavior on color { ColorAnimation { duration: Theme.quick } }
    Behavior on border.color { ColorAnimation { duration: Theme.quick } }

    // Xuất hiện: mờ dần và phóng nhẹ. Không đụng x/y vì Grid mới là nơi đặt vị trí.
    Component.onCompleted: appear.start()
    ParallelAnimation {
        id: appear
        NumberAnimation { target: root; property: "opacity"; to: 1
                          duration: Theme.slow; easing.type: Easing.OutCubic }
        NumberAnimation { target: root; property: "scale"; to: 1.0
                          duration: Theme.slow; easing.type: Easing.OutCubic }
    }

    // Ô ảnh: chưa có ảnh riêng cho từng bản chơi nên dùng một mảng màu, không mượn ảnh giả.
    Rectangle {
        id: thumb
        anchors { top: parent.top; left: parent.left; right: parent.right; margins: 1 }
        height: 92
        radius: Theme.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#243a2c" }
            GradientStop { position: 1.0; color: "#16211a" }
        }

        // Vài khối mờ: đủ để ô ảnh trông có chủ ý, không phải một mảng trống vì lỗi.
        Row {
            anchors { right: parent.right; bottom: parent.bottom; margins: 12 }
            spacing: 6
            Repeater {
                model: 3
                Rectangle {
                    width: 16; height: 16; radius: 3
                    color: Theme.accent
                    opacity: 0.10 + index * 0.05
                }
            }
        }

        Rectangle {
            anchors { left: parent.left; top: parent.top; margins: 10 }
            width: 30; height: 30; radius: 8
            color: playHover.hovered ? Theme.accent : "#b3000000"
            Behavior on color { ColorAnimation { duration: Theme.quick } }
            Text { anchors.centerIn: parent; text: "▶"; color: "white"; font.pixelSize: 12 }
            HoverHandler { id: playHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { enabled: root.playable; onTapped: root.playRequested() }
        }
    }

    // Gỡ hai bước: bấm thùng rác thì hiện "Gỡ?", bấm lần nữa mới gỡ thật. Rời chuột là huỷ.
    Rectangle {
        anchors { right: parent.right; top: thumb.bottom; margins: 10 }
        visible: root.removable
        opacity: hover.hovered ? 1 : 0
        width: removeText.width + 16; height: 24; radius: 6
        color: root.confirmingRemove ? Theme.danger : "transparent"
        Behavior on opacity { NumberAnimation { duration: Theme.quick } }
        Text {
            id: removeText
            anchors.centerIn: parent
            text: root.confirmingRemove ? "Gỡ?" : "🗑"
            font.pixelSize: 12; font.bold: root.confirmingRemove
            color: root.confirmingRemove ? "white" : (trashHover.hovered ? Theme.danger : Theme.textMuted)
        }
        HoverHandler { id: trashHover; cursorShape: Qt.PointingHandCursor }
        TapHandler {
            onTapped: {
                if (root.confirmingRemove) { root.confirmingRemove = false; root.removeRequested(); }
                else root.confirmingRemove = true;
            }
        }
    }

    Column {
        anchors { top: thumb.bottom; left: parent.left; right: parent.right; margins: 14 }
        spacing: 6
        Text {
            text: root.label; color: Theme.text; font.pixelSize: 14; font.bold: true
            width: parent.width; elide: Text.ElideRight
        }
        Text {
            text: root.loaderLabel + "  ·  " + root.versionId
            width: parent.width; elide: Text.ElideRight
            color: Theme.textMuted; font.pixelSize: 11
        }
    }

    HoverHandler { id: hover; onHoveredChanged: if (!hovered) root.confirmingRemove = false }
}
