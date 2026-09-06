import QtQuick

/*
  Popup báo đang làm việc, góc dưới phải, dùng chung cho mọi trang: hiện khi bất kỳ cầu nối nào
  bận (tải phiên bản, chạy installer, tìm/cài mod, đăng nhập). Trượt lên khi có việc, trượt
  xuống khi xong. Chữ là tiến độ thật từ lõi; không có tiến độ thì chỉ nói "Đang xử lý".
*/
Rectangle {
    id: toast
    // Game đang chạy thì cầu nối vẫn bận (chờ tiến trình) nhưng không phải "đang tải": ẩn.
    readonly property bool active: (bridge.busy && !bridge.gameRunning) || contentBridge.busy || catalogBridge.busy
    // Việc nào đang chạy thì nói việc đó; nhiều việc cùng lúc thì ưu tiên cái nặng nhất.
    readonly property string activity: bridge.busy && !bridge.gameRunning ? bridge.activity
                                     : catalogBridge.busy ? catalogBridge.activity
                                     : contentBridge.busy ? contentBridge.activity : ""
    readonly property bool hasFraction: bridge.progressFraction > 0 && bridge.progressFraction < 1

    width: 320
    height: 70
    radius: Theme.radiusSmall
    color: "#f2111713"
    border.color: Theme.border
    border.width: 1
    anchors { right: parent.right; bottom: parent.bottom; margins: Theme.gap }
    anchors.bottomMargin: active ? Theme.gap : -height - 10
    opacity: active ? 1 : 0
    Behavior on anchors.bottomMargin { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
    Behavior on opacity { NumberAnimation { duration: Theme.normal } }
    // Xong việc: chờ toast trượt đi rồi mới xoá chữ, để không thấy chữ nhảy về rỗng lúc còn hiện.
    onActiveChanged: if (!active) clearLater.restart()
    Timer { id: clearLater; interval: Theme.normal + 50; onTriggered: if (!toast.active) bridge.clearProgress() }

    // Vòng quay: một cung xanh xoay đều — dấu hiệu "còn sống" ngay cả khi không có % .
    Item {
        id: spinner
        width: 26; height: 26
        anchors { left: parent.left; leftMargin: 14; verticalCenter: parent.verticalCenter }
        Repeater {
            model: 8
            Rectangle {
                width: 3; height: 7; radius: 1.5
                x: spinner.width / 2 - width / 2; y: 0
                color: Theme.accent
                opacity: 0.25 + 0.75 * index / 7
                transform: Rotation { origin.x: 1.5; origin.y: spinner.height / 2; angle: index * 45 }
            }
        }
        RotationAnimation on rotation {
            running: toast.active; loops: Animation.Infinite
            from: 0; to: 360; duration: 1000
        }
    }

    Column {
        anchors { left: spinner.right; leftMargin: 12; right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
        spacing: 5
        Text {
            width: parent.width
            text: toast.activity
            color: Theme.text; font.pixelSize: 12; font.bold: true; elide: Text.ElideRight
        }
        Text {
            width: parent.width
            visible: bridge.progressText.length > 0
            text: bridge.progressText
            color: Theme.textMuted; font.pixelSize: 11; elide: Text.ElideRight
        }
        Rectangle {
            width: parent.width; height: 3; radius: 1.5
            color: Theme.border
            Rectangle {
                height: parent.height; radius: 1.5
                width: toast.hasFraction ? parent.width * bridge.progressFraction : parent.width
                color: Theme.accent
                opacity: toast.hasFraction ? 1 : 0.35
                Behavior on width { NumberAnimation { duration: Theme.quick } }
            }
        }
    }
}
