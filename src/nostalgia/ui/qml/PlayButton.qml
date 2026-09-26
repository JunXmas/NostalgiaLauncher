import QtQuick

/* Nút chơi lớn, kèm hộp chọn bản chơi dính liền bên dưới — đúng bố cục bản mẫu.

   Khi còn thiếu thứ gì để chơi được, khối này KHÔNG chỉ làm mờ nút: nó nói thiếu gì và đưa
   luôn nút đi làm việc đó. Nút xám câm là lý do người dùng bỏ đi — họ không đoán ra rằng
   phải thêm tài khoản, vì chỗ thêm tài khoản nằm ở trang khác. */
Column {
    id: root
    property var instances: []
    property int chosenIndex: 0
    property bool playable: true
    // Game đang chạy: cùng nút đó thành DỪNG (đỏ), bấm là kill tiến trình game.
    property bool running: false
    // "account" | "instance" | "" — thứ còn thiếu, do trang chủ tính và truyền xuống.
    property string missingKind: ""
    signal clicked()
    signal stopRequested()
    signal picked(int index)
    signal createRequested()
    signal addAccountRequested()

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

    // Có bản chơi VÀ có tài khoản: hộp chọn bản. Còn thiếu thì thay bằng khối hành động
    // bên dưới — hộp chọn lúc đó chỉ là thứ gây nhiễu, vì chọn xong vẫn không chơi được.
    Dropdown {
        objectName: "homeInstancePicker"
        visible: root.instances.length > 0 && root.missingKind !== "account"
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
    /* Khối "còn thiếu": nói thiếu gì, và nút bấm đi làm đúng việc đó.

       Một việc một lúc — thiếu cả tài khoản lẫn bản chơi thì hỏi tài khoản trước, vì tạo bản
       chơi xong mà chưa đăng nhập thì vẫn không bấm CHƠI được. */
    Rectangle {
        objectName: "missingAction"
        visible: root.missingKind !== ""
        width: parent.width
        height: 66
        radius: Theme.radiusSmall
        color: "#d9111713"
        border.color: Theme.accent
        border.width: 2

        Column {
            anchors { left: parent.left; right: parent.right; margins: 10; verticalCenter: parent.verticalCenter }
            spacing: 7
            Text {
                width: parent.width
                text: root.missingKind === "account" ? "Cần một tài khoản để chơi"
                                                     : "Chưa có bản chơi nào"
                color: Theme.text; font.pixelSize: Theme.fontBody; font.bold: true
            }
            ActionButton {
                objectName: "missingActionButton"
                width: parent.width
                height: 30
                label: root.missingKind === "account" ? "Thêm tài khoản" : "Tạo bản chơi"
                onClicked: root.missingKind === "account" ? root.addAccountRequested()
                                                          : root.createRequested()
            }
        }
    }
}
