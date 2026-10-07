import QtQuick
import "../" as Legacy

Item {
    id: root
    opacity: visible ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: GlassTheme.normal } }
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
            color: GlassTheme.alpha(GlassTheme.background, 0.75)
        }
    }
    Glass {
        objectName: "deviceLoginSurface"
        backdrop: Legacy.Theme.modalBackdrop
        blurOpacity: 0.9
        finishOpacity: 0.65
        width: 480
        height: form.height + 64
        anchors.centerIn: parent
        padding: 32
        Column {
            id: form
            width: parent.width
            spacing: 22
            ProviderLogo { width: 32; height: 32; provider: "microsoft" }
            Text {
                text: "Đăng nhập Microsoft"
                color: GlassTheme.text
                font.family: GlassTheme.displayFont
                font.pixelSize: GlassTheme.fontLogin
                font.weight: Font.DemiBold
            }
            Text {
                width: parent.width
                wrapMode: Text.Wrap
                text: "Mở trang Microsoft, nhập mã bên dưới và đăng nhập tài khoản sở hữu Minecraft Java."
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: GlassTheme.fontControl
                lineHeight: 1.4
            }
            Rectangle {
                width: parent.width
                height: 82
                radius: 14
                color: GlassTheme.inputSurface
                border.color: GlassTheme.stroke
                TextEdit {
                    id: codeText
                    anchors.centerIn: parent
                    text: root.code
                    color: GlassTheme.accent
                    font.family: "monospace"
                    font.pixelSize: GlassTheme.fontCode
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
