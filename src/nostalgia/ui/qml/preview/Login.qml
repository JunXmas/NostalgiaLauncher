import QtQuick
import "../" as Legacy

Item {
    id: root
    signal enterRequested
    property string mode: "choose"
    property string failure: ""
    property bool needsTotp: false
    readonly property bool busy: bridge.busy || accountBridge.busy
    function submitOffline() {
        if (offlineName.text.trim() && !root.busy)
            bridge.addOfflineAccount(offlineName.text.trim());
    }
    function submitEly() {
        if (!email.text.trim() || !password.text || root.busy)
            return;
        failure = "";
        accountBridge.signInEly(email.text.trim(), password.text, totp.text);
    }
    Connections {
        target: accountBridge
        function onFailed(message) {
            root.failure = message;
            password.text = "";
        }
        function onTwoFactorRequired() {
            root.needsTotp = true;
            root.failure = Legacy.Tr.phrase("Nhập mã xác thực hai bước để tiếp tục.");
        }
        function onElySignedIn(playerName) {
            password.text = "";
            totp.text = "";
        }
    }
    Connections {
        target: bridge
        function onFailed(message) {
            root.failure = message;
        }
    }
    Row {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 48
        spacing: 12
        Image {
            width: 32
            height: 32
            source: "../assets/logo.png"
            mipmap: true
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: "Nostalgia"
            color: GlassTheme.text
            font.family: GlassTheme.font
            font.pixelSize: GlassTheme.fontBrand
            font.weight: Font.DemiBold
        }
    }
    Row {
        id: welcomeActions
        objectName: "welcomeActions"
        anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 40; spacing: 12
        LanguagePicker {}
        GuideButton { topicId: "start"; anchors.verticalCenter: parent.verticalCenter }
    }
    Column {
        x: 64
        y: Math.max(150, (parent.height - height) * 0.46)
        width: Math.max(240, root.width - card.width - 180)
        spacing: 22
        Row {
            spacing: 8
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 6
                height: 6
                radius: 3
                color: GlassTheme.accent
            }
            Text {
                text: Legacy.Tr.phrase("MINECRAFT, THEO CÁCH CỦA BẠN")
                color: GlassTheme.accent
                font.family: GlassTheme.font
                font.pixelSize: GlassTheme.fontNote
                font.letterSpacing: 2
            }
        }
        Text {
            width: parent.width
            text: Legacy.Tr.phrase("Một thế giới.\nVô vàn\nkhởi đầu.")
            color: GlassTheme.text
            font.family: GlassTheme.font
            font.pixelSize: root.width < 1200 ? 54 : 76
            font.weight: Font.DemiBold
            font.letterSpacing: -3
            lineHeight: 1.07
        }
        Text {
            width: Math.min(360, parent.width)
            wrapMode: Text.WordWrap
            text: Legacy.Tr.phrase("Chơi, khám phá và trở lại những điều bạn yêu. Tất cả bắt đầu ở đây.")
            color: GlassTheme.muted
            font.family: GlassTheme.font
            font.pixelSize: GlassTheme.fontAction
            lineHeight: 1.55
        }
    }
    Glass {
        id: card
        objectName: "loginCard"
        backdrop: Legacy.Theme.modalBackdrop
        blurOpacity: 0.9
        finishOpacity: 0.65
        color: GlassTheme.alpha(GlassTheme.surface, 0.74)
        width: Math.min(440, root.width * 0.42)
        height: Math.min(root.height - Math.max(170, 2 * (welcomeActions.y + welcomeActions.height + 16)), form.height + 72)
        anchors.right: parent.right
        anchors.rightMargin: 64
        anchors.verticalCenter: parent.verticalCenter
        padding: 32
        InertialScroll {
            anchors.fill: parent
            contentHeight: form.height
            Column {
                id: form
                width: parent.width
                spacing: 22
                Column {
                    width: parent.width
                    spacing: 10
                    Text {
                        text: root.mode === "choose" ? Legacy.Tr.phrase("Chào mừng về nhà.") : root.mode === "ely" ? Legacy.Tr.phrase("Đăng nhập Ely.by") : Legacy.Tr.phrase("Chơi ngoại tuyến")
                        color: GlassTheme.text
                        font.family: GlassTheme.font
                        font.pixelSize: GlassTheme.fontResult
                        font.weight: Font.DemiBold
                    }
                    Text {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: root.mode === "choose" ? Legacy.Tr.phrase("Chọn tài khoản để bắt đầu hành trình.") : root.mode === "ely" ? Legacy.Tr.phrase("Sử dụng tài khoản và skin Ely.by của bạn.") : Legacy.Tr.phrase("Đặt tên nhân vật để chơi trên máy này.")
                        color: GlassTheme.muted
                        font.family: GlassTheme.font
                        font.pixelSize: GlassTheme.fontControl
                        lineHeight: 1.4
                    }
                }
                Column {
                    visible: root.mode === "choose"
                    width: parent.width
                    spacing: 12
                    Button {
                        objectName: "loginGoogleService"
                        provider: "google"
                        width: parent.width
                        label: socialBridge.signedIn ? Legacy.Tr.phrase("Google đã kết nối ✓") : Legacy.Tr.phrase("Tiếp tục với Google  ↗")
                        clickable: socialBridge.configured && !socialBridge.busy && !socialBridge.signingIn && !socialBridge.signedIn
                        onClicked: socialBridge.signIn()
                    }
                    PaymentText {
                        width: parent.width
                        text: socialBridge.signingIn || Legacy.Tr.message(socialBridge.note) ? Legacy.Tr.message(socialBridge.note) : socialBridge.configured ? Legacy.Tr.phrase("Tài khoản Nostalgia · đồng bộ bạn bè và Plus đã mua. Minecraft dùng tài khoản bên dưới.") : Legacy.Tr.phrase("Google chưa khả dụng trong bản thử này. Bạn vẫn có thể đăng nhập Minecraft bên dưới.")
                        color: GlassTheme.muted
                        font.pixelSize: GlassTheme.fontNote
                    }
                    Button {
                        objectName: "loginMicrosoft"
                        provider: "microsoft"
                        width: parent.width
                        height: 50
                        primary: true
                        label: root.busy ? Legacy.Tr.phrase("Đang kết nối…") : Legacy.Tr.phrase("Tiếp tục với Microsoft")
                        clickable: !root.busy
                        onClicked: {
                            root.failure = "";
                            bridge.signInMicrosoft();
                        }
                    }
                    Text {
                        width: parent.width
                        text: Legacy.Tr.phrase("Dành cho tài khoản sở hữu Minecraft Java.")
                        color: GlassTheme.muted
                        font.family: GlassTheme.font
                        font.pixelSize: GlassTheme.fontNote
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Item {
                        width: parent.width
                        height: 16
                    }
                    Rectangle {
                        width: parent.width
                        height: 1
                        color: GlassTheme.stroke
                    }
                    Item {
                        width: parent.width
                        height: 4
                    }
                    Button {
                        objectName: "loginEly"
                        width: parent.width
                        height: 48
                        label: Legacy.Tr.phrase("Đăng nhập Ely.by")
                        clickable: !root.busy
                        onClicked: {
                            root.failure = "";
                            root.mode = "ely";
                        }
                    }
                    Button {
                        objectName: "loginOffline"
                        width: parent.width
                        label: Legacy.Tr.phrase("Chơi ngoại tuyến")
                        quiet: true
                        clickable: !root.busy
                        onClicked: {
                            root.failure = "";
                            root.mode = "offline";
                        }
                    }
                }
                Column {
                    visible: root.mode === "offline"
                    width: parent.width
                    spacing: 16
                    Input {
                        id: offlineName
                        objectName: "loginOfflineName"
                        width: parent.width
                        placeholder: Legacy.Tr.phrase("Tên nhân vật")
                        onAccepted: root.submitOffline()
                    }
                    Button {
                        objectName: "loginOfflineSubmit"
                        width: parent.width
                        label: root.busy ? Legacy.Tr.phrase("Đang tạo…") : Legacy.Tr.phrase("Bắt đầu chơi")
                        primary: true
                        clickable: !!offlineName.text.trim() && !root.busy
                        onClicked: root.submitOffline()
                    }
                }
                Column {
                    visible: root.mode === "ely"
                    width: parent.width
                    spacing: 14
                    Input {
                        id: email
                        objectName: "loginElyEmail"
                        width: parent.width
                        placeholder: Legacy.Tr.phrase("Email hoặc tên Ely.by")
                    }
                    Input {
                        id: password
                        objectName: "loginElyPassword"
                        width: parent.width
                        placeholder: Legacy.Tr.phrase("Mật khẩu")
                        echoMode: TextInput.Password
                        onAccepted: root.submitEly()
                    }
                    Input {
                        id: totp
                        objectName: "loginTotp"
                        visible: root.needsTotp
                        width: parent.width
                        placeholder: Legacy.Tr.phrase("Mã xác thực 2 bước")
                        onAccepted: root.submitEly()
                    }
                    Button {
                        objectName: "loginElySubmit"
                        width: parent.width
                        label: root.busy ? Legacy.Tr.phrase("Đang đăng nhập…") : Legacy.Tr.phrase("Đăng nhập")
                        primary: true
                        clickable: !!email.text.trim() && !!password.text && !root.busy
                        onClicked: root.submitEly()
                    }
                    Button {
                        width: parent.width
                        label: Legacy.Tr.phrase("Tạo tài khoản Ely.by ↗")
                        quiet: true
                        onClicked: Qt.openUrlExternally("https://account.ely.by/register")
                    }
                }
                Text {
                    visible: !!Legacy.Tr.message(root.failure)
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: Legacy.Tr.message(root.failure)
                    color: GlassTheme.danger
                    font.family: GlassTheme.font
                    font.pixelSize: GlassTheme.fontBody
                }
                Button {
                    visible: root.mode !== "choose"
                    width: parent.width
                    quiet: true
                    label: Legacy.Tr.phrase("← Quay lại")
                    clickable: !root.busy
                    onClicked: {
                        root.mode = "choose";
                        root.failure = "";
                        password.text = "";
                        totp.text = "";
                    }
                }
                Text {
                    visible: root.mode === "choose"
                    width: parent.width
                    text: Legacy.Tr.phrase("Tài khoản của bạn. Thế giới của bạn.")
                    color: GlassTheme.muted
                    font.family: GlassTheme.font
                    font.pixelSize: GlassTheme.fontLabel
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }
    Text {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: 48
        text: "NOSTALGIA LAUNCHER    /    JAVA EDITION"
        color: GlassTheme.muted
        font.family: GlassTheme.font
        font.pixelSize: GlassTheme.fontCaption
        font.letterSpacing: 1.7
    }
    Button {
        objectName: "loginExplore"
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 40
        label: Legacy.Tr.phrase("Khám phá trước  →")
        quiet: true
        clickable: !root.busy
        onClicked: root.enterRequested()
    }
}
