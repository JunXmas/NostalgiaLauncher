import QtQuick
import "preview" as Preview

/* Thêm tài khoản: chọn Microsoft (mã thiết bị, hộp SignInDialog sẵn có), Ely.by (email + mật
   khẩu, hỏi thêm mã 2FA khi cần), hoặc ngoại tuyến (chỉ tên). Mật khẩu chỉ đi qua bridge. */
Item {
    id: dialog
    visible: false
    z: 100
    Keys.onEscapePressed: dialog.visible = false
    property string mode: "pick"   // pick | ely | offline
    property bool needsTotp: false
    property string failure: ""

    function openDialog() { mode = "pick"; needsTotp = false; failure = ""; emailField.text = ""; passwordField.text = ""; totpField.text = ""; nameField.text = ""; visible = true; box.forceActiveFocus(); }

    Connections {
        target: accountBridge
        function onElySignedIn(playerName) { dialog.visible = false; }
        function onTwoFactorRequired() { dialog.needsTotp = true; dialog.failure = Tr.phrase("Tài khoản bật xác thực hai lớp — nhập mã từ ứng dụng TOTP."); }
        function onFailed(message) { dialog.failure = message; }
    }
    Connections {
        target: bridge
        function onSignInFinished(playerName) { dialog.visible = false; }
    }

    MouseArea {
        anchors.fill: parent
        onWheel: function(event) { event.accepted = true; }
        onClicked: if (!accountBridge.busy) dialog.visible = false
        Rectangle { anchors.fill: parent; color: "#b3000000" }
    }
    DialogFrame {
        id: box
        objectName: "AddAccountDialogSurface"
        anchors.centerIn: parent
        width: Math.min(Theme.modern ? 560 * Theme.textScale : 440, parent.width - 40)
        height: Math.min(contentColumn.implicitHeight + 52, parent.height - 40)
        backdrop: Theme.modern ? Theme.modalBackdrop : null
        blurOpacity: 0.9
        finishOpacity: 0.65
        radius: Theme.radius
        color: Qt.rgba(Theme.surface.r, Theme.surface.g, Theme.surface.b, Theme.modern ? 0.78 : 1)
        border.color: Theme.border
        MouseArea { anchors.fill: parent }

        Preview.InertialScroll {
            id: accountFormScroll
            objectName: "accountFormScroll"
            anchors.fill: parent; anchors.margins: 26
            contentHeight: contentColumn.implicitHeight
        Column {
            id: contentColumn
            width: accountFormScroll.width
            spacing: 14
            Text { text: Tr.phrase("Thêm tài khoản"); color: Theme.text; font.family: Theme.modern ? "Manrope" : Theme.sans; font.pixelSize: Theme.fontTitle; font.bold: true }

            // ----- chọn loại -----
            Column {
                visible: dialog.mode === "pick"; width: parent.width; spacing: 10
                Repeater {
                    model: [
                        { key: "microsoft", title: "Microsoft", text: Tr.phrase("Tài khoản premium: đăng nhập bằng mã trên trang Microsoft.") },
                        { key: "ely",       title: "Ely.by",    text: Tr.phrase("Non-premium: tên duy nhất, skin/cape riêng hiện trong game.") },
                        { key: "offline",   title: Tr.phrase("Ngoại tuyến"), text: Tr.phrase("Chỉ nhập tên. Không skin riêng, tên có thể trùng người khác.") }
                    ]
                    Rectangle {
                        readonly property color providerTint: pickArea.containsMouse ? Theme.surfaceHigh : Theme.surface
                        width: parent.width; height: Theme.modern ? Math.max(58, providerText.implicitHeight + 24) : 58; radius: Theme.radiusSmall
                        color: Qt.rgba(providerTint.r, providerTint.g, providerTint.b, Theme.modern ? (pickArea.containsMouse ? 0.78 : 0.58) : 1)
                        border.color: Theme.border
                        Behavior on color { ColorAnimation { duration: Theme.quick } }
                        Preview.ProviderLogo { x: 14; anchors.verticalCenter: parent.verticalCenter; width: 26; height: 26; provider: modelData.key; visible: modelData.key === "microsoft" }
                        Column {
                            id: providerText
                            width: parent.width - (modelData.key === "microsoft" ? 68 : 28)
                            anchors { left: parent.left; leftMargin: modelData.key === "microsoft" ? 54 : 14; verticalCenter: parent.verticalCenter }
                            spacing: 3
                            Text { text: modelData.title; color: Theme.text; font.pixelSize: Theme.fontHeading; font.bold: true }
                            Text { width: parent.width; wrapMode: Text.WordWrap; text: modelData.text; color: Theme.textMuted; font.pixelSize: Theme.fontBody }
                        }
                        MouseArea {
                            id: pickArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (modelData.key === "microsoft") { dialog.visible = false; bridge.signInMicrosoft(); }
                                else dialog.mode = modelData.key;
                            }
                        }
                    }
                }
            }

            // ----- Ely.by -----
            Column {
                visible: dialog.mode === "ely"; width: parent.width; spacing: 10
                Text { text: Tr.phrase("ELY.BY — EMAIL HOẶC TÊN"); color: Theme.textMuted; font.pixelSize: Theme.fontLabel; font.letterSpacing: 1.2 }
                TextField { id: emailField; objectName: "elyEmailField"; width: parent.width; placeholder: "ban@example.com" }
                Text { text: Tr.phrase("MẬT KHẨU"); color: Theme.textMuted; font.pixelSize: Theme.fontLabel; font.letterSpacing: 1.2 }
                TextField { id: passwordField; objectName: "elyPasswordField"; width: parent.width; placeholder: "••••••••"; echoMode: TextInput.Password; onAccepted: dialog.submitEly() }
                Text { visible: dialog.needsTotp; text: Tr.phrase("MÃ 2FA"); color: Theme.textMuted; font.pixelSize: Theme.fontLabel; font.letterSpacing: 1.2 }
                TextField { id: totpField; visible: dialog.needsTotp; width: 160; placeholder: "123456"; onAccepted: dialog.submitEly() }
                Text { visible: Tr.message(dialog.failure) !== ""; width: parent.width; wrapMode: Text.WordWrap; text: Tr.message(dialog.failure); color: Theme.danger; font.pixelSize: Theme.fontBody }
                Text {
                    width: parent.width; wrapMode: Text.WordWrap
                    text: Tr.phrase("Chưa có tài khoản? Bấm \"Đăng ký ↗\" để mở ely.by. Mật khẩu chỉ gửi tới Ely.by, launcher không lưu.")
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody
                }
                Flow {
                    width: parent.width; spacing: 8
                    ActionButton { objectName: "elySignInButton"; label: accountBridge.busy ? Tr.phrase("Đang đăng nhập...") : Tr.phrase("Đăng nhập")
                                   clickable: !accountBridge.busy && emailField.text.trim() !== "" && passwordField.text !== ""; onClicked: dialog.submitEly() }
                    /* Đăng ký phải mở trình duyệt, không có cách nào khác: ely.by đòi xác nhận
                       email. Dựng form đăng ký trong launcher chỉ là đẩy họ ra trình duyệt
                       chậm hơn một bước, và là một chỗ nữa để mật khẩu đi qua tay ta. */
                    ActionButton {
                        objectName: "elyRegisterButton"
                        primary: false; label: Tr.phrase("Đăng ký ↗")
                        /* account.ely.by, KHÔNG phải ely.by: ely.by là catalog skin, mọi
                           thứ tài khoản nằm ở subdomain kia. `ely.by/register` ra 404. */
                        readonly property url target: "https://account.ely.by/register"
                        onClicked: Qt.openUrlExternally(target)
                    }
                    ActionButton { primary: false; label: Tr.phrase("Quay lại"); onClicked: dialog.mode = "pick" }
                }
            }

            // ----- ngoại tuyến -----
            Column {
                visible: dialog.mode === "offline"; width: parent.width; spacing: 10
                Text { text: Tr.phrase("TÊN NGOẠI TUYẾN"); color: Theme.textMuted; font.pixelSize: Theme.fontLabel; font.letterSpacing: 1.2 }
                TextField { id: nameField; width: parent.width; placeholder: Tr.phrase("vd. Steve"); onAccepted: dialog.submitOffline() }
                Flow {
                    width: parent.width; spacing: 8
                    ActionButton { label: Tr.phrase("Thêm"); clickable: nameField.text.trim() !== ""; onClicked: dialog.submitOffline() }
                    ActionButton { primary: false; label: Tr.phrase("Quay lại"); onClicked: dialog.mode = "pick" }
                }
            }
        }
        }
    }

    function submitEly() {
        if (emailField.text.trim() === "" || passwordField.text === "") return;
        dialog.failure = "";
        accountBridge.signInEly(emailField.text, passwordField.text, totpField.text);
    }
    function submitOffline() {
        if (nameField.text.trim() === "") return;
        bridge.addOfflineAccount(nameField.text.trim());
        dialog.visible = false;
    }
}
