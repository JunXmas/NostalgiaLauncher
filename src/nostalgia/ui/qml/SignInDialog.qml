import QtQuick

/*
  Hộp thoại mã thiết bị của Microsoft: hiện mã to, nút mở trang đăng nhập, nút sao chép.
  Lõi đang chờ ở luồng nền; huỷ ở đây là huỷ thật (CancelToken), không phải chỉ ẩn hộp.
*/
Item {
    id: dialog
    objectName: "signInDialog"
    visible: false
    z: 110
    property string userCode: ""
    property string verificationUrl: ""

    Connections {
        target: bridge
        function onDeviceCodeReady(userCode, verificationUrl) {
            dialog.userCode = userCode; dialog.verificationUrl = verificationUrl; dialog.visible = true;
        }
        function onSignInFinished(playerName) { dialog.visible = false; }
        function onFailed(message) { dialog.visible = false; }
    }

    Rectangle { anchors.fill: parent; color: "#b3000000"; TapHandler { } }

    Rectangle {
        anchors.centerIn: parent
        width: 440; height: 300
        radius: Theme.radius
        color: Theme.surface
        border.color: Theme.border
        border.width: 1

        Column {
            anchors { fill: parent; margins: 26 }
            spacing: 14
            Text { text: "Đăng nhập Microsoft"; color: Theme.text; font.pixelSize: 18; font.bold: true }
            Text {
                width: parent.width; wrapMode: Text.WordWrap
                text: "Mở trang bên dưới, nhập mã này rồi đăng nhập bằng tài khoản Microsoft có Minecraft. Hộp này tự đóng khi xong."
                color: Theme.textMuted; font.pixelSize: 12
            }
            Rectangle {
                width: parent.width; height: 64; radius: Theme.radiusSmall
                color: Theme.surfaceHigh; border.color: Theme.accent
                TextEdit {
                    id: codeText
                    anchors.centerIn: parent
                    text: dialog.userCode
                    readOnly: true; selectByMouse: true
                    color: Theme.accent; font.pixelSize: 30; font.bold: true; font.letterSpacing: 6
                    font.family: "monospace"
                }
            }
            Text { text: dialog.verificationUrl; color: Theme.textMuted; font.pixelSize: 11 }
            Row {
                spacing: 8
                ActionButton {
                    label: "Mở trang Microsoft"
                    onClicked: Qt.openUrlExternally(dialog.verificationUrl)
                }
                ActionButton {
                    primary: false
                    label: "Sao chép mã"
                    onClicked: { codeText.selectAll(); codeText.copy(); codeText.deselect(); }
                }
                ActionButton {
                    primary: false
                    label: "Huỷ"
                    onClicked: { bridge.cancelSignIn(); dialog.visible = false; }
                }
            }
        }
    }
}
