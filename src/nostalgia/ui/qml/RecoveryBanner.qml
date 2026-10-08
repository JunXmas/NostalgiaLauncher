import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    objectName: "errorBanner"
    property string message: ""
    property var owner: null
    height: message ? body.height + 24 : 0
    visible: message.length > 0
    color: Theme.surfaceHigh
    border.color: Theme.danger; border.width: 2
    function report(message, owner) { root.message = message; root.owner = owner; }
    Column {
        id: body
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
        spacing: 10
        Text {
            width: parent.width
            text: Tr.phrase("Không thể hoàn thành thao tác")
            color: Theme.text; font.pixelSize: Theme.fontHeading; font.bold: true
        }
        Text {
            width: parent.width; maximumLineCount: 2; wrapMode: Text.WordWrap; elide: Text.ElideRight
            text: root.message; color: Theme.textMuted; font.pixelSize: Theme.fontBody
        }
        Flow {
            width: parent.width; spacing: 10
            ActionButton {
                objectName: "retryButton"; label: Tr.phrase("Thử lại")
                visible: root.owner !== null && root.owner.canRetry === true
                onClicked: { root.owner.retry(); root.message = ""; }
            }
            ActionButton { primary: false; label: Tr.phrase("Chi tiết & sao chép"); onClicked: details.open() }
            ActionButton { primary: false; label: Tr.phrase("Đóng"); onClicked: root.message = "" }
        }
    }
    Popup {
        id: details
        parent: Overlay.overlay
        x: Math.round((parent.width - width) / 2); y: Math.round((parent.height - height) / 2)
        width: Math.min(760, parent.width - 48); height: Math.min(440, parent.height - 48)
        modal: true; focus: true; padding: 20
        background: DialogFrame { color: Theme.modern ? Qt.rgba(Theme.surface.r, Theme.surface.g, Theme.surface.b, 0.60) : Theme.surface; border.color: Theme.border }
        Column {
            anchors.fill: parent; spacing: 12
            Text { text: Tr.phrase("Chi tiết lỗi"); color: Theme.text; font.pixelSize: Theme.fontTitle; font.bold: true }
            ScrollView {
                width: parent.width; height: parent.height - 110
                TextArea {
                    id: diagnostic; text: root.message; readOnly: true; selectByMouse: true
                    wrapMode: TextEdit.Wrap; color: Theme.text; font.pixelSize: Theme.fontBody
                    background: Rectangle { color: Theme.background }
                }
            }
            Flow {
                width: parent.width; spacing: 12
                ActionButton { label: Tr.phrase("Sao chép chi tiết"); onClicked: { diagnostic.selectAll(); diagnostic.copy(); } }
                ActionButton { primary: false; label: Tr.phrase("Đóng"); onClicked: details.close() }
            }
        }
    }
}
