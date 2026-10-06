import QtQuick

Item {
    id: root
    objectName: "minimalDeviceLogin"
    visible: false
    z: 110
    property string code: ""
    property string url: ""
    Connections {
        target: bridge
        function onDeviceCodeReady(userCode, verificationUrl) {
            root.code = userCode;
            root.url = verificationUrl;
            root.visible = true;
        }
        function onSignInFinished(playerName) {
            root.visible = false;
        }
        function onFailed(message) {
            root.visible = false;
        }
    }
    MouseArea {
        anchors.fill: parent
        Rectangle {
            anchors.fill: parent
            color: "#bb080d11"
        }
    }
    Glass {
        width: 480
        height: form.height + 64
        anchors.centerIn: parent
        padding: 32
        Column {
            id: form
            width: parent.width
            spacing: 22
            Text {
                text: "Đăng nhập Microsoft"
                color: GlassTheme.text
                font.family: GlassTheme.font
                font.pixelSize: 25
                font.weight: Font.DemiBold
            }
            Text {
                width: parent.width
                wrapMode: Text.Wrap
                text: "Mở trang Microsoft, nhập mã bên dưới và đăng nhập tài khoản sở hữu Minecraft Java."
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: 14
                lineHeight: 1.4
            }
            Rectangle {
                width: parent.width
                height: 82
                radius: 14
                color: "#66121b1f"
                border.color: GlassTheme.stroke
                TextEdit {
                    id: codeText
                    anchors.centerIn: parent
                    text: root.code
                    color: GlassTheme.accent
                    font.family: "monospace"
                    font.pixelSize: 32
                    font.letterSpacing: 5
                    readOnly: true
                    selectByMouse: true
                }
            }
            Button {
                width: parent.width
                label: "Mở trang Microsoft  ↗"
                primary: true
                onClicked: Qt.openUrlExternally(root.url)
            }
            Row {
                width: parent.width
                spacing: 12
                Button {
                    width: (parent.width - 12) / 2
                    label: "Sao chép mã"
                    quiet: true
                    onClicked: {
                        codeText.selectAll();
                        codeText.copy();
                        codeText.deselect();
                    }
                }
                Button {
                    width: (parent.width - 12) / 2
                    objectName: "cancelMicrosoft"
                    label: "Hủy đăng nhập"
                    quiet: true
                    onClicked: {
                        bridge.cancelSignIn();
                        root.visible = false;
                    }
                }
            }
        }
    }
}
