import QtQuick

/* Thêm tài khoản: chọn Microsoft (mã thiết bị, hộp SignInDialog sẵn có), Ely.by (email + mật
   khẩu, hỏi thêm mã 2FA khi cần), hoặc ngoại tuyến (chỉ tên). Mật khẩu chỉ đi qua bridge. */
Item {
    id: dialog
    visible: false
    z: 100
    property string mode: "pick"   // pick | ely | offline
    property bool needsTotp: false
    property string failure: ""

    function openDialog() { mode = "pick"; needsTotp = false; failure = ""; emailField.text = ""; passwordField.text = ""; totpField.text = ""; nameField.text = ""; visible = true; }

    Connections {
        target: accountBridge
        function onElySignedIn(playerName) { dialog.visible = false; }
        function onTwoFactorRequired() { dialog.needsTotp = true; dialog.failure = "Tài khoản bật xác thực hai lớp — nhập mã từ ứng dụng TOTP."; }
        function onFailed(message) { dialog.failure = message; }
    }
    Connections {
        target: bridge
        function onSignInFinished(playerName) { dialog.visible = false; }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: if (!accountBridge.busy) dialog.visible = false
        Rectangle { anchors.fill: parent; color: "#b3000000" }
    }
    Rectangle {
        anchors.centerIn: parent
        width: 440; height: contentColumn.height + 52
        radius: Theme.radius; color: Theme.surface; border.color: Theme.border
        MouseArea { anchors.fill: parent }

        Column {
            id: contentColumn
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 26 }
            spacing: 14
            Text { text: "Thêm tài khoản"; color: Theme.text; font.pixelSize: 18; font.bold: true }

            // ----- chọn loại -----
            Column {
                visible: dialog.mode === "pick"; width: parent.width; spacing: 10
                Repeater {
                    model: [
                        { key: "microsoft", title: "Microsoft", text: "Tài khoản premium: đăng nhập bằng mã trên trang Microsoft." },
                        { key: "ely",       title: "Ely.by",    text: "Non-premium: tên duy nhất, skin/cape riêng hiện trong game." },
                        { key: "offline",   title: "Ngoại tuyến", text: "Chỉ nhập tên. Không skin riêng, tên có thể trùng người khác." }
                    ]
                    Rectangle {
                        width: parent.width; height: 58; radius: Theme.radiusSmall
                        color: pickArea.containsMouse ? Theme.surfaceHigh : Theme.surface; border.color: Theme.border
                        Column {
                            anchors { left: parent.left; leftMargin: 14; verticalCenter: parent.verticalCenter }
                            spacing: 3
                            Text { text: modelData.title; color: Theme.text; font.pixelSize: 13; font.bold: true }
                            Text { text: modelData.text; color: Theme.textMuted; font.pixelSize: 11 }
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
                Text { text: "ELY.BY — EMAIL HOẶC TÊN"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                TextField { id: emailField; objectName: "elyEmailField"; width: parent.width; placeholder: "ban@example.com" }
                Text { text: "MẬT KHẨU"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                TextField { id: passwordField; objectName: "elyPasswordField"; width: parent.width; placeholder: "••••••••"; echoMode: TextInput.Password; onAccepted: dialog.submitEly() }
                Text { visible: dialog.needsTotp; text: "MÃ 2FA"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                TextField { id: totpField; visible: dialog.needsTotp; width: 160; placeholder: "123456"; onAccepted: dialog.submitEly() }
                Text { visible: dialog.failure !== ""; width: parent.width; wrapMode: Text.WordWrap; text: dialog.failure; color: Theme.danger; font.pixelSize: 11 }
                Text {
                    width: parent.width; wrapMode: Text.WordWrap
                    text: "Chưa có tài khoản? Đăng ký miễn phí tại ely.by. Mật khẩu chỉ gửi tới Ely.by, launcher không lưu."
                    color: Theme.textMuted; font.pixelSize: 11
                }
                Row {
                    spacing: 8
                    ActionButton { objectName: "elySignInButton"; label: accountBridge.busy ? "Đang đăng nhập..." : "Đăng nhập"
                                   clickable: !accountBridge.busy && emailField.text.trim() !== "" && passwordField.text !== ""; onClicked: dialog.submitEly() }
                    ActionButton { primary: false; label: "Quay lại"; onClicked: dialog.mode = "pick" }
                }
            }

            // ----- ngoại tuyến -----
            Column {
                visible: dialog.mode === "offline"; width: parent.width; spacing: 10
                Text { text: "TÊN NGOẠI TUYẾN"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                TextField { id: nameField; width: parent.width; placeholder: "vd. Steve"; onAccepted: dialog.submitOffline() }
                Row {
                    spacing: 8
                    ActionButton { label: "Thêm"; clickable: nameField.text.trim() !== ""; onClicked: dialog.submitOffline() }
                    ActionButton { primary: false; label: "Quay lại"; onClicked: dialog.mode = "pick" }
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
