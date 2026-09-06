import QtQuick

/*
  Ô hồ sơ ở cột phải: danh sách tài khoản thật, chọn cái để chơi, gỡ, và hai cách thêm —
  đăng nhập Microsoft (mã thiết bị) hoặc tên ngoại tuyến.

  Không có "Level 24 / XP" như bản mẫu: Minecraft không có thứ đó, và ta không vẽ số giả.
*/
Panel {
    id: root
    property var accounts: []
    property string activePlayerName: ""
    signal addAccountRequested(string name)
    signal microsoftSignInRequested()
    signal accountChosen(string name)
    signal removeRequested(string name)

    title: "HỒ SƠ"

    Column {
        anchors.fill: parent
        spacing: 8

        Repeater {
            model: root.accounts
            Rectangle {
                id: accountRow
                readonly property bool active: modelData.playerName === root.activePlayerName
                width: parent.width; height: 40; radius: Theme.radiusSmall
                color: active ? Theme.accentSoft : (rowHover.hovered ? Theme.surfaceHigh : "transparent")
                border.color: active ? Theme.accent : "transparent"
                Behavior on color { ColorAnimation { duration: Theme.quick } }

                Row {
                    anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
                    spacing: 10
                    Rectangle {
                        width: 26; height: 26; radius: 6; color: Theme.accentDeep
                        anchors.verticalCenter: parent.verticalCenter
                        Text {
                            anchors.centerIn: parent
                            text: modelData.playerName.charAt(0).toUpperCase()
                            color: "white"; font.pixelSize: 12; font.bold: true
                        }
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1
                        Text { text: modelData.playerName; color: Theme.text; font.pixelSize: 12; font.bold: true }
                        Text {
                            text: modelData.accountKind === "microsoft" ? "Microsoft" : "Ngoại tuyến"
                            color: Theme.textMuted; font.pixelSize: 10
                        }
                    }
                }
                Text {
                    anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
                    text: "✕"; font.pixelSize: 11
                    color: removeHover.hovered ? Theme.danger : Theme.textMuted
                    opacity: rowHover.hovered ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.quick } }
                    HoverHandler { id: removeHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: root.removeRequested(modelData.playerName) }
                }
                HoverHandler { id: rowHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.accountChosen(modelData.playerName) }
            }
        }

        Text {
            visible: root.accounts.length === 0
            width: parent.width
            text: "Chưa có tài khoản."
            color: Theme.textMuted; font.pixelSize: 11
        }

        Item { width: 1; height: 4 }

        ActionButton {
            width: parent.width
            label: "Đăng nhập Microsoft"
            clickable: !bridge.busy
            onClicked: root.microsoftSignInRequested()
        }
        Row {
            width: parent.width
            spacing: 8
            TextField {
                id: nameField
                width: parent.width - offlineButton.width - 8
                placeholder: "Tên ngoại tuyến"
                onAccepted: root.addAccountRequested(text)
            }
            ActionButton {
                id: offlineButton
                primary: false
                label: "Thêm"
                onClicked: root.addAccountRequested(nameField.text)
            }
        }
    }
}
