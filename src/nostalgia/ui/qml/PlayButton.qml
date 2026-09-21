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

    // Thứ tự hiện trong khay: bản vừa chơi gần nhất lên đầu, còn lại giữ nguyên thứ tự chữ
    // cái của `instances`. Mảng này là chỉ số TRONG `instances`, nên `picked()` vẫn phát ra
    // chỉ số gốc — phần còn lại của trang chủ không cần biết khay đã sắp lại.
    readonly property var order: root.instances
        .map(function (_, index) { return index; })
        .sort(function (first, second) {
            var gap = (root.instances[second].lastPlayedAt || 0)
                    - (root.instances[first].lastPlayedAt || 0);
            return gap !== 0 ? gap : first - second;  // hoà thì giữ thứ tự cũ, đừng xáo trộn
        })
    // Chỉ số bản vừa chơi; -1 khi chưa ai chơi lần nào (máy mới) — lúc đó không gắn nhãn.
    readonly property int recentIndex: root.order.length > 0
                                       && (root.instances[root.order[0]].lastPlayedAt || 0) > 0
                                       ? root.order[0] : -1

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
        // Đóng lại chỉ thấy một dòng: viên "N bản" là thứ duy nhất nói rằng còn bản khác.
        badge: root.instances.length > 1 ? root.instances.length + " bản" : ""
        markedIndex: root.order.indexOf(root.recentIndex)
        markLabel: "vừa chơi"
        model: root.order.map(function (index) {
            var instance = root.instances[index];
            return instance.label + "  (" + instance.versionId + ")";
        })
        currentIndex: root.order.indexOf(root.chosenIndex)
        onActivated: function (position) { root.picked(root.order[position]); }
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
