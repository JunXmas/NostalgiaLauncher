import QtQuick

/* Nút chơi lớn, kèm hộp chọn bản chơi dính liền bên dưới — đúng bố cục bản mẫu. */
Column {
    id: root
    property var instances: []
    property int chosenIndex: 0
    property bool playable: true
    signal clicked()
    signal picked(int index)
    signal createRequested()

    spacing: 0
    width: 300

    Rectangle {
        width: parent.width
        height: 64
        radius: Theme.radiusSmall
        color: root.playable ? (press.pressed ? Theme.accentDeep : Theme.accent) : Theme.surfaceHigh
        scale: press.pressed ? 0.985 : (hover.hovered && root.playable ? 1.015 : 1.0)
        Behavior on color { ColorAnimation { duration: Theme.quick } }
        Behavior on scale { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }

        Text {
            anchors.centerIn: parent
            text: "CHƠI  ▶"
            color: root.playable ? "#06210f" : Theme.textMuted
            font.pixelSize: 24; font.bold: true; font.letterSpacing: 2
        }

        HoverHandler { id: hover; enabled: root.playable; cursorShape: Qt.PointingHandCursor }
        TapHandler { id: press; enabled: root.playable; onTapped: root.clicked() }
    }

    // Có bản chơi: hộp chọn. Chưa có: một dòng dẫn sang trang tạo.
    Dropdown {
        objectName: "homeInstancePicker"
        visible: root.instances.length > 0
        dropUp: true
        width: parent.width
        height: 40
        model: root.instances.map(function (instance) { return instance.label + "  (" + instance.versionId + ")"; })
        currentIndex: root.chosenIndex
        onActivated: function (index) { root.picked(index); }
    }
    Rectangle {
        visible: root.instances.length === 0
        width: parent.width
        height: 40
        radius: Theme.radiusSmall
        color: createHover.hovered ? Theme.surfaceHigh : "#d9111713"
        border.color: Theme.border
        Text {
            anchors.centerIn: parent
            text: "Chưa có bản chơi — bấm để tạo"
            color: Theme.textMuted; font.pixelSize: 12
        }
        HoverHandler { id: createHover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: root.createRequested() }
    }
}
