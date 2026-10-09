import QtQuick
import QtQuick.Dialogs
import "preview" as Preview

/*
  Nhập/chọn skin chỉ thay bản xem trước. Nút Lưu trong SkinPanel mới áp dụng tài khoản.
*/
Item {
    id: library
    property var shown: ({})
    property bool hasShown: false
    property var viewport: null
    readonly property var entries: accountBridge.skinLibrary
    readonly property string shownDigest: hasShown && shown.skinDigest !== undefined ? shown.skinDigest : ""

    implicitHeight: header.height + 10 + Math.max(grid.implicitHeight, emptyLabel.visible ? emptyLabel.implicitHeight + 14 : 40)

    /* Nhan trái neo trái, nút phải neo phải — KHÔNG dùng một Row với spacer `width - 330`.
       Cái đệm cứng đó chỉ đúng ở đúng một bề rộng: hẹp hơn thì nó âm và nút tràn ra ngoài ô,
       rộng hơn thì hai nút trôi vào giữa. Neo hai đầu thì mọi bề rộng đều đúng. */
    Flow {
        id: header
        width: parent.width; spacing: 12
        Text { height: 36 * Theme.textScale; verticalAlignment: Text.AlignVCenter; text: Tr.phrase("Thư viện skin") + " · " + library.entries.length; color: Theme.text; font.family: Theme.modern ? "Inter" : Theme.sans; font.pixelSize: Theme.fontBody; font.bold: true }
        Preview.Button { objectName: "importSkinButton"; label: Tr.phrase("Thêm skin  +"); clickable: !skinEditor.busy; onClicked: importDialog.open() }
    }

    Flow {
        id: grid
        objectName: "skinLibraryGrid"
        anchors { top: header.bottom; topMargin: 10; left: parent.left; right: parent.right }
        spacing: 10
        Repeater {
            model: library.entries
            Rectangle {
                id: card
                readonly property bool inUse: library.shownDigest !== "" && modelData.entryId === library.shownDigest
                readonly property bool inPreview: modelData.entryId === skinEditor.details.entryId
                readonly property bool inViewport: {
                    if (typeof library === "undefined" || !library) return false;
                    if (!library.viewport) return true;
                    var top = card.y + grid.y + library.y - library.viewport.contentY;
                    return top + height > 0 && top < library.viewport.height;
                }
                width: 148 * (Theme.modern ? Theme.textScale : 1); height: 224 * (Theme.modern ? Theme.textScale : 1); radius: Theme.radiusSmall
                color: inUse ? Theme.accentSoft : (cardHover.hovered ? Theme.surfaceHigh : Theme.surface)
                border.color: inPreview ? Theme.accent : Theme.border
                Behavior on border.color { ColorAnimation { duration: Theme.quick } }
                Column {
                    anchors { top: parent.top; topMargin: 12; horizontalCenter: parent.horizontalCenter }
                    spacing: 6
                    SkinFigure {
                        objectName: "skinLibraryFigure"
                        pixel: 3; width: 64 * (Theme.modern ? Theme.textScale : 1); height: width * 2
                        source: modelData.skinFile; slim: card.inPreview ? skinEditor.details.slim : modelData.slim
                        anchors.horizontalCenter: parent.horizontalCenter
                        interactive: false
                        renderEnabled: card.inViewport
                    }
                    Text {
                        width: card.width - 16; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight
                        text: modelData.name; color: Theme.text; font.pixelSize: Theme.fontBody; font.bold: true
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: card.inPreview && skinEditor.details.skinDirty ? "Đang xem trước" : card.inUse ? Tr.phrase("Đang dùng") : modelData.sourceLabel + (modelData.slim ? " · slim" : "")
                        color: card.inPreview ? Theme.accent : Theme.textMuted; font.pixelSize: Theme.fontLabel
                    }
                }
                Rectangle {
                    anchors { top: parent.top; right: parent.right; margins: 6 }
                    width: 8; height: 8; radius: 4; color: Theme.accent; visible: card.inUse
                }
                // Chọn để xem trước hoặc gỡ khỏi kho; không upload từ thẻ.
                Row {
                    anchors { bottom: parent.bottom; bottomMargin: 6; horizontalCenter: parent.horizontalCenter }
                    spacing: 8
                    opacity: Theme.modern || cardHover.hovered ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.quick } }
                    Preview.Button {
                        objectName: "previewSkin-" + modelData.entryId
                        visible: library.hasShown
                        height: 30 * Theme.textScale; label: "Xem trước"; clickable: !skinEditor.busy
                        onClicked: skinEditor.selectSkin(modelData.entryId)
                    }
                    Preview.Button {
                        quiet: true; danger: true; width: 28; height: 30 * Theme.textScale; label: "×"; clickable: !skinEditor.busy
                        onClicked: accountBridge.removeLibrarySkin(modelData.entryId)
                    }
                }
                HoverHandler { id: cardHover }
            }
        }
    }
    Text {
        id: emptyLabel
        visible: library.entries.length === 0
        anchors { top: header.bottom; topMargin: 14; left: parent.left; right: parent.right }
        wrapMode: Text.WordWrap
        text: Tr.phrase("Chưa có skin nào. Bấm \"Thêm skin\" để chọn file PNG; skin tải về cho tài khoản Microsoft/Ely.by cũng tự vào đây.")
        color: Theme.textMuted; font.pixelSize: Theme.fontBody
    }

    FileDialog {
        id: importDialog
        title: Tr.phrase("Chọn file skin PNG")
        nameFilters: ["Ảnh PNG (*.png)"]
        onAccepted: skinEditor.importSkin("" + selectedFile)
    }
}
