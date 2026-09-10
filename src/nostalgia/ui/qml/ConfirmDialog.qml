import QtQuick

/*
  Hộp hỏi lại dùng chung. Đặt ở Main.qml (cấp cửa sổ) và lộ cho mọi trang qua context property
  `confirmDialog`, nên phủ cả thanh bên: mở ra là không bấm nhầm được thứ gì phía sau. Chỉ đóng
  bằng Thôi / Esc — bấm màn tối KHÔNG đóng (từng làm người dùng tưởng hộp "xuyên" xuống trang).
  Nuốt cả rê chuột và cuộn để phía sau không sáng lên hay trôi.

  `ask(title, message, acceptAction)`: đồng ý thì gọi `acceptAction()` rồi phát `accepted()`.
*/
Item {
    id: dialog
    visible: false
    z: 200
    property string title: ""
    property string message: ""
    property string acceptLabel: "Đồng ý"
    property string cancelLabel: "Thôi"
    property var acceptAction: null
    signal accepted()

    function ask(title, message, acceptAction) {
        dialog.title = title;
        dialog.message = message;
        dialog.acceptAction = acceptAction || null;
        dialog.visible = true;
        box.forceActiveFocus();
        notifier.playUi("open");
    }
    function dismiss() {
        dialog.visible = false;
        dialog.acceptAction = null;
        notifier.playUi("back");
    }
    function accept() {
        var action = dialog.acceptAction;
        dialog.visible = false;
        dialog.acceptAction = null;
        if (action) action();
        dialog.accepted();
    }

    // Màn tối: nuốt bấm (mọi nút), rê và cuộn — không làm gì cả.
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.AllButtons
        onWheel: function (wheel) { wheel.accepted = true; }
        Rectangle { anchors.fill: parent; color: "#b3000000" }
    }
    Rectangle {
        id: box
        anchors.centerIn: parent
        width: 420; height: contentColumn.height + 52
        radius: Theme.radius; color: Theme.surface; border.color: Theme.border
        focus: true
        Keys.onEscapePressed: dialog.dismiss()
        Keys.onReturnPressed: dialog.accept()
        MouseArea { anchors.fill: parent; hoverEnabled: true }

        Column {
            id: contentColumn
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 26 }
            spacing: 14
            Text { text: dialog.title; color: Theme.text; font.pixelSize: 17; font.bold: true }
            Text {
                objectName: "confirmMessage"
                width: parent.width; wrapMode: Text.WordWrap
                text: dialog.message; color: Theme.textMuted; font.pixelSize: 12; lineHeight: 1.3
            }
            Row {
                anchors.right: parent.right
                spacing: 10
                ActionButton {
                    objectName: "confirmCancel"
                    primary: false; label: dialog.cancelLabel
                    onClicked: dialog.dismiss()
                }
                ActionButton {
                    objectName: "confirmAccept"
                    label: dialog.acceptLabel
                    onClicked: dialog.accept()
                }
            }
        }
    }
}
