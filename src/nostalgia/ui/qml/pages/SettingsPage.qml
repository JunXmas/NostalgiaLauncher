import QtQuick
import "../"

/* CÀI ĐẶT: thông tin chung và công tắc âm thanh thông báo. Thư viện CurseForge đi qua máy chủ
   của dự án, không cần khoá. */
Item {
    id: page
    signal navigate(int pageIndex)

    Item {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right; margins: Theme.gap }
        height: 50
        Text {
            anchors { left: parent.left; verticalCenter: parent.verticalCenter }
            text: "Cài đặt"; color: Theme.text; font.pixelSize: 22; font.bold: true
        }
    }

    UpdatePanel {
        id: updatePanel
        anchors { top: header.bottom; left: parent.left; right: parent.right; margins: Theme.gap; topMargin: 6 }
    }

    Panel {
        anchors { top: updatePanel.bottom; left: parent.left; right: parent.right; bottom: parent.bottom
                  margins: Theme.gap; topMargin: Theme.gap }
        title: "CHUNG"

        Column {
            anchors { left: parent.left; right: parent.right }
            spacing: 14
            Row {
                spacing: 10
                Text { text: "Phiên bản launcher"; color: Theme.textMuted; font.pixelSize: 12; width: 160 }
                Text { text: settingsBridge.launcherVersion; color: Theme.text; font.pixelSize: 12 }
            }
            Row {
                spacing: 10
                Text { text: "Thư mục dữ liệu"; color: Theme.textMuted; font.pixelSize: 12; width: 160
                       anchors.verticalCenter: parent.verticalCenter }
                Text {
                    text: settingsBridge.dataDir; color: Theme.text; font.pixelSize: 12
                    elide: Text.ElideMiddle; width: Math.min(520, page.width - 360)
                    anchors.verticalCenter: parent.verticalCenter
                }
                ActionButton { primary: false; label: "Mở thư mục"; onClicked: settingsBridge.openDataFolder() }
            }
            Text {
                width: Math.min(parent.width, 720)
                wrapMode: Text.WordWrap
                text: "Thư viện mod và modpack duyệt CurseForge qua máy chủ của Nostalgia, không cần khoá API."
                color: Theme.textMuted; font.pixelSize: 12; lineHeight: 1.3
            }
            Rectangle { width: parent.width; height: 1; color: Theme.border }
            Row {
                spacing: 10
                Text { text: "Âm thanh thông báo"; color: Theme.textMuted; font.pixelSize: 12; width: 160
                       anchors.verticalCenter: parent.verticalCenter }
                Toggle {
                    objectName: "notificationSoundToggle"
                    anchors.verticalCenter: parent.verticalCenter
                    checked: settingsBridge.notificationSound
                    onToggled: function (checked) { settingsBridge.setNotificationSound(checked); }
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Chuông ngắn khi game khởi động, thoát, hoặc tải xong phiên bản."
                    color: Theme.textMuted; font.pixelSize: 11
                }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.border }
            Row {
                spacing: 10
                Text { text: "Discord Rich Presence"; color: Theme.textMuted; font.pixelSize: 12; width: 160
                       anchors.verticalCenter: parent.verticalCenter }
                Toggle {
                    objectName: "discordToggle"
                    anchors.verticalCenter: parent.verticalCenter
                    checked: settingsBridge.discordPresence
                    onToggled: function (checked) { settingsBridge.setDiscord(checked, discordIdField.text); }
                }
                TextField {
                    id: discordIdField
                    objectName: "discordIdField"
                    width: 220
                    placeholder: "Application ID"
                    text: settingsBridge.discordApplicationId
                    onAccepted: settingsBridge.setDiscord(settingsBridge.discordPresence, text)
                    onActiveFocusChanged: if (!activeFocus) settingsBridge.setDiscord(settingsBridge.discordPresence, text)
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: presenceBridge.statusText
                    color: presenceBridge.connected ? Theme.accent : Theme.textMuted; font.pixelSize: 11
                }
            }
            Text {
                width: Math.min(parent.width, 720)
                wrapMode: Text.WordWrap
                text: "Khi game chạy, hồ sơ Discord hiện \"Đang chơi <bản chơi>\" kèm thời gian. Cần Discord đang mở và một Application ID tự tạo tại discord.com/developers (Applications → New Application → General Information)."
                color: Theme.textMuted; font.pixelSize: 11; lineHeight: 1.3
            }
        }
    }
}
