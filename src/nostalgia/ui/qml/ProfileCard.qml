import QtQuick

/*
  Ô hồ sơ ở cột phải: danh sách tài khoản thật, chọn cái để chơi, gỡ, và hai cách thêm —
  đăng nhập Microsoft (mã thiết bị) hoặc tên ngoại tuyến.

  Cao theo nội dung (`implicitHeight`), không phải hằng số: một hằng số sai là ô "Thêm" tràn
  ra đè lên ô bên dưới — lỗi đã gặp. Nhiều tài khoản thì thu gọn còn tài khoản đang chọn; nút
  khối đá ▾ ở góc phải ô đó xoè danh sách ra.
*/
Panel {
    id: root
    property var accounts: []
    property string activePlayerName: ""
    signal addAccountRequested(string name)
    signal microsoftSignInRequested()
    signal accountChosen(string name)
    signal removeRequested(string name)

    property bool expanded: false
    readonly property bool collapsible: root.accounts.length > 1
    readonly property var shownAccounts: (root.collapsible && !root.expanded)
        ? root.accounts.filter(function (account) { return account.playerName === root.activePlayerName; })
        : root.accounts

    title: "HỒ SƠ"
    implicitHeight: root.contentTop + column.implicitHeight + Theme.pad

    Column {
        id: column
        objectName: "profileColumn"
        width: parent.width
        spacing: 8

        Repeater {
            model: root.shownAccounts
            Rectangle {
                id: accountRow
                readonly property bool active: modelData.playerName === root.activePlayerName
                readonly property bool hasToggle: active && root.collapsible
                width: parent.width; height: 40; radius: Theme.radiusSmall
                color: active ? Theme.accentSoft : (rowHover.hovered ? Theme.surfaceHigh : "transparent")
                border.color: active ? Theme.accent : "transparent"
                Behavior on color { ColorAnimation { duration: Theme.quick } }

                Row {
                    anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
                    spacing: 10
                    SkinFace {
                        size: 26
                        anchors.verticalCenter: parent.verticalCenter
                        source: accountBridge.accountNamed(modelData.playerName).skinFile || ""
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1
                        Text { text: modelData.playerName; color: Theme.text; font.pixelSize: 12; font.bold: true }
                        Text {
                            text: modelData.accountKind === "microsoft" ? "Microsoft"
                                  : modelData.accountKind === "ely" ? "Ely.by" : "Ngoại tuyến"
                            color: Theme.textMuted; font.pixelSize: 10
                        }
                    }
                }

                // Gỡ tài khoản: chỉ khi danh sách đang xoè (thu gọn thì hàng duy nhất là cái đang dùng).
                Text {
                    visible: root.expanded || !root.collapsible
                    anchors { right: parent.right; rightMargin: accountRow.hasToggle ? 50 : 10; verticalCenter: parent.verticalCenter }
                    text: "✕"; font.pixelSize: 11
                    color: removeHover.hovered ? Theme.danger : Theme.textMuted
                    opacity: rowHover.hovered ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.quick } }
                    HoverHandler { id: removeHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: root.removeRequested(modelData.playerName) }
                }

                // Nút xoè/thu gọn kiểu khối đá, ở góc phải ô tài khoản đang chọn.
                Rectangle {
                    objectName: "profileChevron"
                    visible: accountRow.hasToggle
                    anchors { right: parent.right; rightMargin: 6; verticalCenter: parent.verticalCenter }
                    width: 38; height: 26; radius: 3
                    color: toggleHover.hovered ? "#5a5247" : "#4a443c"
                    border.color: "#2e2a25"; border.width: 2
                    Text {
                        anchors.centerIn: parent
                        text: root.expanded ? "▴" : "▾ " + root.accounts.length
                        color: "#e8dcc8"; font.pixelSize: 11; font.bold: true
                    }
                    HoverHandler { id: toggleHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: root.expanded = !root.expanded }
                }

                HoverHandler { id: rowHover; cursorShape: Qt.PointingHandCursor }
                TapHandler {
                    onTapped: {
                        if (root.collapsible && !root.expanded) root.expanded = true;
                        else { root.accountChosen(modelData.playerName); if (root.collapsible) root.expanded = false; }
                    }
                }
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
                objectName: "offlineNameField"
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
