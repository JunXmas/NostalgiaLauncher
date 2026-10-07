import QtQuick
import QtQuick.Controls as Controls

// Keep ask()/visible compatible with existing pages; the modal itself belongs to Overlay.
Item {
    id: dialog
    visible: false
    property string title: ""
    property string message: ""
    property string acceptLabel: Tr.phrase("Đồng ý")
    property string cancelLabel: Tr.phrase("Thôi")
    property var acceptAction: null
    signal accepted()
    function ask(title, message, acceptAction) {
        dialog.title = title;
        dialog.message = message;
        dialog.acceptAction = acceptAction || null;
        dialog.visible = true;
        notifier.playUi("open");
    }
    function dismiss() {
        dialog.visible = false;
        dialog.acceptAction = null;
        notifier.playUi("back");
    }
    function accept() {
        if (!dialog.visible) return;
        var action = dialog.acceptAction;
        dialog.visible = false;
        dialog.acceptAction = null;
        if (action) action();
        dialog.accepted();
    }
    Controls.Popup {
        id: modal
        objectName: "confirmationModal"
        parent: Controls.Overlay.overlay
        z: 10000
        visible: dialog.visible
        modal: true; dim: true; focus: true
        closePolicy: Controls.Popup.NoAutoClose
        padding: 26
        width: Math.min(480 * Theme.textScale, parent ? parent.width - 48 : 480)
        height: Math.min(contents.implicitHeight + padding * 2, parent ? parent.height - 48 : 500)
        x: parent ? (parent.width - width) / 2 : 0
        y: parent ? (parent.height - height) / 2 : 0
        onOpened: contentItem.forceActiveFocus()
        Controls.Overlay.modal: Rectangle {
            color: "#b3080b12"
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.AllButtons
                onWheel: function (wheel) { wheel.accepted = true; }
            }
        }
        background: DialogFrame { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
        contentItem: Flickable {
            contentHeight: contents.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            Keys.onEscapePressed: dialog.dismiss()
            Keys.onReturnPressed: dialog.accept()
            Column {
                id: contents
                width: parent.width
                spacing: 16
                Text {
                    width: parent.width; wrapMode: Text.Wrap
                    text: dialog.title; color: Theme.text
                    font.family: Theme.sans; font.pixelSize: Theme.fontTitle; font.bold: true
                }
                Text {
                    objectName: "confirmMessage"
                    width: parent.width; wrapMode: Text.Wrap
                    text: dialog.message; color: Theme.textMuted
                    font.family: Theme.sans; font.pixelSize: Theme.fontBody; lineHeight: 1.3
                }
                Flow {
                    width: parent.width; spacing: 10
                    layoutDirection: Qt.RightToLeft
                    ActionButton { objectName: "confirmAccept"; label: dialog.acceptLabel; onClicked: dialog.accept() }
                    ActionButton { objectName: "confirmCancel"; primary: false; label: dialog.cancelLabel; onClicked: dialog.dismiss() }
                }
            }
        }
    }
}
