import QtQuick

/*
  Dải "có bản mới" chạy ngang đầu vùng nội dung, thấy ở MỌI trang.

  Trước đây bản mới chỉ nằm ở CÀI ĐẶT → CẬP NHẬT, cộng một toast bốn giây bảo người dùng tự
  đi tìm chỗ đó. Người dùng không đi. Dải này mang đúng hai nút cần thiết (Tải / Cài và mở
  lại) ra ngay chỗ họ đang nhìn; đóng được, và đóng rồi thì im tới lần mở launcher sau.
*/
Rectangle {
    id: root
    objectName: "updateBanner"
    // Trạng thái đáng chiếm chỗ trên màn hình; "checking"/"idle"/"failed" thì không.
    readonly property bool active: !dismissed && (updateBridge.state === "available"
                                   || updateBridge.state === "downloading"
                                   || updateBridge.state === "ready")
    property bool dismissed: false
    readonly property bool canSelfUpdate: updateBridge.canSelfUpdate
    // Cờ này là điều kiện hiện của nút, tách ra để test đọc được: `visible` của QML là
    // hiện-thật-sự (luôn false khi cây chưa vào cửa sổ), nên không kiểm được ràng buộc.
    // Lúc đang tải thì ẩn nút: việc đã chạy, bấm thêm không thêm được gì.
    readonly property bool canUpdate: active && updateBridge.state === "available"

    height: active ? 52 : 0
    visible: active
    clip: true
    color: Theme.accentSoft
    border.color: Theme.accent
    border.width: 1

    Row {
        anchors { left: parent.left; leftMargin: Theme.pad; verticalCenter: parent.verticalCenter }
        spacing: 12
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: "⬆"; color: Theme.accent; font.pixelSize: 15; font.bold: true
        }
        Text {
            objectName: "updateBannerText"
            anchors.verticalCenter: parent.verticalCenter
            text: updateBridge.state === "downloading"
                  ? "Đang tải bản " + updateBridge.latestVersion + "… "
                    + Math.round(updateBridge.progressFraction * 100) + "%"
                  : updateBridge.state === "ready"
                  ? "Đang cài bản " + updateBridge.latestVersion + ", launcher sắp mở lại…"
                  : "Có bản mới " + updateBridge.latestVersion
            color: Theme.text; font.pixelSize: 13; font.bold: true
        }
    }

    Row {
        anchors { right: parent.right; rightMargin: Theme.pad; verticalCenter: parent.verticalCenter }
        spacing: 10
        ActionButton {
            objectName: "bannerUpdateButton"
            anchors.verticalCenter: parent.verticalCenter
            visible: root.canUpdate
            // Một nút, một nhịp: tải → tráo → mở lại. Gói không tự tráo được thì mở trang tải.
            label: root.canSelfUpdate ? "⬇  Cập nhật ngay" : "Mở trang tải"
            onClicked: updateBridge.updateNow()
        }
        Text {
            objectName: "updateBannerDismiss"
            anchors.verticalCenter: parent.verticalCenter
            text: "✕"; color: Theme.textMuted; font.pixelSize: 14
            MouseArea {
                anchors { fill: parent; margins: -8 }
                cursorShape: Qt.PointingHandCursor
                onClicked: root.dismissed = true
            }
        }
    }
}
