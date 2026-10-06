import QtQuick

Panel {
    id: root
    objectName: "onboardingCard"
    signal navigate(int pageIndex)
    readonly property bool hasAccount: bridge.activePlayerName.length > 0
    readonly property bool hasInstance: bridge.instances.length > 0
    implicitHeight: content.height + 48
    Column {
        id: content
        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 24 }
        spacing: 16
        Text { text: Tr.phrase("Bắt đầu cuộc phiêu lưu"); color: Theme.text; font.pixelSize: Theme.fontTitle; font.bold: true }
        Text {
            width: parent.width; wrapMode: Text.WordWrap
            text: Tr.phrase("Chọn tài khoản, tạo hoặc nhập bản chơi, rồi bắt đầu chơi.")
            color: Theme.textMuted; font.pixelSize: Theme.fontBody
        }
        Row {
            spacing: 18
            Text { text: (root.hasAccount ? "✓ " : "1. ") + Tr.phrase("Tài khoản"); color: root.hasAccount ? Theme.brand : Theme.textMuted; font.pixelSize: Theme.fontBody }
            Text { text: (root.hasInstance ? "✓ " : "2. ") + Tr.phrase("Bản chơi"); color: root.hasInstance ? Theme.brand : Theme.textMuted; font.pixelSize: Theme.fontBody }
            Text { text: "3. " + Tr.phrase("Chơi"); color: Theme.textMuted; font.pixelSize: Theme.fontBody }
        }
        Flow {
            width: parent.width; spacing: 12
            ActionButton {
                objectName: "onboardingPrimary"
                label: root.hasAccount ? Tr.phrase("Tạo bản chơi đầu tiên") : Tr.phrase("Thêm tài khoản")
                onClicked: root.navigate(root.hasAccount ? 1 : 3)
            }
            ActionButton {
                primary: false
                label: root.hasAccount ? Tr.phrase("Khám phá modpack") : Tr.phrase("Chọn bản chơi trước")
                onClicked: root.navigate(root.hasAccount ? 2 : 1)
            }
        }
    }
}
