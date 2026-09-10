import QtQuick

/* Nút chơi lớn, kèm hộp chọn bản chơi dính liền bên dưới — đúng bố cục bản mẫu. */
Column {
    id: root
    property var instances: []
    property int chosenIndex: 0
    property bool playable: true
    // Game đang chạy: cùng nút đó thành DỪNG (đỏ), bấm là kill tiến trình game.
    property bool running: false
    signal clicked()
    signal stopRequested()
    signal picked(int index)
    signal createRequested()

    spacing: 0
    width: 300

    // Cùng khối kiểu minecraft.net như mọi nút, chỉ to hơn.
    ActionButton {
        objectName: "playButton"
        width: parent.width
        height: 64
        fontSize: 24
        label: root.running ? "DỪNG  ■" : "CHƠI  ▶"
        danger: root.running
        clickable: root.running || root.playable
        onClicked: root.running ? root.stopRequested() : root.clicked()
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
