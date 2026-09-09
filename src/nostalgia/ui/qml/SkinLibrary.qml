import QtQuick
import QtQuick.Dialogs

/*
  Thư viện skin: mọi skin launcher từng thấy (tải về cho tài khoản, đã upload, tự nhập) xếp
  thành lưới thẻ; thẻ đang dùng cho tài khoản được chọn có viền xanh và nhãn "Đang dùng".
  "Thêm skin" là nút duy nhất để đưa file PNG vào: Microsoft thì upload lên Mojang (và vào kho),
  tài khoản khác thì vào kho rồi dùng ngay; "Dùng" trên thẻ cũng theo đúng luật đó.
*/
Item {
    id: library
    property var shown: ({})
    property bool hasShown: false
    property bool slimImport: false
    readonly property var entries: accountBridge.skinLibrary
    readonly property string shownDigest: hasShown && shown.skinDigest !== undefined ? shown.skinDigest : ""

    implicitHeight: header.height + 10 + Math.max(grid.implicitHeight, 40)

    Row {
        id: header
        width: parent.width; height: 30; spacing: 12
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: "THƯ VIỆN SKIN"; color: Theme.accent; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.2
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: library.entries.length + " skin"; color: Theme.textMuted; font.pixelSize: 11
        }
        Item { width: header.width - 330; height: 1 }
        CheckRow {
            anchors.verticalCenter: parent.verticalCenter
            label: "Slim"; checked: library.slimImport
            onToggled: library.slimImport = !library.slimImport
        }
        ActionButton {
            objectName: "importSkinButton"
            label: "📁  Thêm skin"
            onClicked: importDialog.open()
        }
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
                width: 132; height: 132; radius: Theme.radiusSmall
                color: inUse ? Theme.accentSoft : (cardHover.hovered ? Theme.surfaceHigh : Theme.surface)
                border.color: inUse ? Theme.accent : Theme.border
                Column {
                    anchors { top: parent.top; topMargin: 12; horizontalCenter: parent.horizontalCenter }
                    spacing: 6
                    SkinFace { size: 44; source: modelData.skinFile; anchors.horizontalCenter: parent.horizontalCenter }
                    Text {
                        width: card.width - 16; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight
                        text: modelData.name; color: Theme.text; font.pixelSize: 11; font.bold: true
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: card.inUse ? "Đang dùng" : modelData.sourceLabel + (modelData.slim ? " · slim" : "")
                        color: card.inUse ? Theme.accent : Theme.textMuted; font.pixelSize: 10
                    }
                }
                Rectangle {
                    anchors { top: parent.top; right: parent.right; margins: 6 }
                    width: 8; height: 8; radius: 4; color: Theme.accent; visible: card.inUse
                }
                // Hai nút chỉ hiện khi trỏ vào: Dùng (khi chưa dùng) và ✕ gỡ khỏi kho.
                Row {
                    anchors { bottom: parent.bottom; bottomMargin: 6; horizontalCenter: parent.horizontalCenter }
                    spacing: 8
                    opacity: cardHover.hovered ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.quick } }
                    ActionButton {
                        visible: !card.inUse && library.hasShown
                        height: 24; fontSize: 10; label: "Dùng"
                        onClicked: accountBridge.applyLibrarySkin(library.shown.playerName, modelData.entryId)
                    }
                    ActionButton {
                        primary: false; height: 24; fontSize: 10; label: "✕"
                        onClicked: accountBridge.removeLibrarySkin(modelData.entryId)
                    }
                }
                HoverHandler { id: cardHover }
            }
        }
    }
    Text {
        visible: library.entries.length === 0
        anchors { top: header.bottom; topMargin: 14; left: parent.left }
        text: "Chưa có skin nào. Bấm \"Thêm skin\" để chọn file PNG; skin tải về cho tài khoản Microsoft/Ely.by cũng tự vào đây."
        color: Theme.textMuted; font.pixelSize: 11
    }

    FileDialog {
        id: importDialog
        title: "Chọn file skin PNG"
        nameFilters: ["Ảnh PNG (*.png)"]
        onAccepted: accountBridge.addSkin(library.hasShown ? library.shown.playerName : "", selectedFile, library.slimImport)
    }
}
