import QtQuick

/*
  Hộp hỏi lại dùng chung: tiêu đề, một câu hỏi, hai nút. Mở bằng `ask(title, message)`; bấm nút
  chính phát `accepted()`, bấm nút phụ / màn tối / Esc thì đóng im lặng. Không giữ trạng thái gì
  ngoài chữ đang hiện — bên gọi tự nhớ mình đang hỏi về cái gì.
*/
Item {
    id: dialog
    visible: false
    z: 100
    property string title: ""
    property string message: ""
    property string acceptLabel: "Đồng ý"
    property string cancelLabel: "Thôi"
    signal accepted()

    function ask(title, message) {
        dialog.title = title;
        dialog.message = message;
        dialog.visible = true;
        notifier.playUi("open");
    }
    function dismiss() {
        dialog.visible = false;
        notifier.playUi("back");
    }

    MouseArea {
        anchors.fill: parent
        onClicked: dialog.dismiss()
        Rectangle { anchors.fill: parent; color: "#b3000000" }
    }
    Rectangle {
        anchors.centerIn: parent
        width: 420; height: contentColumn.height + 52
        radius: Theme.radius; color: Theme.surface; border.color: Theme.border
        MouseArea { anchors.fill: parent }
        Keys.onEscapePressed: dialog.dismiss()

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
                    onClicked: { dialog.visible = false; dialog.accepted(); }
                }
            }
        }
    }
}
