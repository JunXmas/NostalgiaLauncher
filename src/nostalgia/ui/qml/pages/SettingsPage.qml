import QtQuick
import "../preview" as Preview
import QtQuick.Dialogs
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
        PageTitle {
            anchors { left: parent.left; verticalCenter: parent.verticalCenter }
            caption: Tr.phrase("Cài đặt")
        }
    }

    Flickable {
        anchors { top: header.bottom; left: parent.left; right: parent.right; bottom: parent.bottom; margins: Theme.gap; topMargin: 0 }
        clip: true
        contentHeight: settingsColumn.height
        boundsBehavior: Flickable.StopAtBounds
        Column {
            id: settingsColumn
            width: parent.width; spacing: Theme.gap
            AppearanceSettings { width: parent.width; height: implicitHeight }
    Preview.ServiceSettings { width: parent.width }
    UpdatePanel {
        id: updatePanel
        width: parent.width
    }

    Panel {
        width: parent.width
        height: contentTop + generalSettings.implicitHeight + Theme.pad
        title: Tr.phrase("CHUNG")

        Column {
            id: generalSettings
            anchors { left: parent.left; right: parent.right }
            spacing: 14
            Flow {
                width: parent.width
                spacing: 10
                Text { text: Tr.phrase("Phiên bản launcher"); color: Theme.textMuted; font.pixelSize: Theme.fontBody; width: 210 * Theme.textScale
                        }
                Text { text: settingsBridge.launcherVersion; color: Theme.text; font.pixelSize: Theme.fontBody
                       width: 120;  }
                // Trang CÀI ĐẶT không cuộn được, nên nút ủng hộ đi ghép vào hàng này thay vì
                // thêm hàng mới — hàng cuối cùng đã chạm mép dưới ở cửa sổ 1360×860.
                ActionButton {
                    objectName: "donateButton"
                    primary: false; label: Tr.phrase("Ủng hộ dự án")

                    // Mở hộp có mã QR chứ không nhảy ra trình duyệt: chuyển khoản trong nước
                    // không phải qua thẻ quốc tế.
                    onClicked: donateDialog.open()
                }
                Text {

                    text: Tr.phrase("Launcher miễn phí, không quảng cáo. Ủng hộ là tuỳ tâm.")
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody
                }
            }
            Flow {
                width: parent.width
                spacing: 10
                Text { text: Tr.phrase("Thư mục dữ liệu"); color: Theme.textMuted; font.pixelSize: Theme.fontBody; width: 210 * Theme.textScale
                        }
                Text {
                    text: settingsBridge.dataDir; color: Theme.text; font.pixelSize: Theme.fontBody
                    elide: Text.ElideMiddle; width: Math.max(160, Math.min(520, page.width - 400))

                }
                ActionButton { primary: false; label: Tr.phrase("Mở thư mục"); onClicked: settingsBridge.openDataFolder() }
            }
            Flow {
                width: parent.width
                spacing: 10
                Text { text: Tr.phrase("Thư mục lưu bản chơi"); color: Theme.textMuted; font.pixelSize: Theme.fontBody; width: 210 * Theme.textScale
                        }
                Text {
                    objectName: "gameDirRootText"
                    text: settingsBridge.defaultGameDirRoot || (settingsBridge.dataDir + Tr.phrase("/instances  (mặc định)"))
                    color: settingsBridge.defaultGameDirRoot ? Theme.text : Theme.textMuted; font.pixelSize: Theme.fontBody
                    elide: Text.ElideMiddle; width: Math.max(160, Math.min(420, page.width - 500))

                }
                ActionButton { primary: false; label: Tr.phrase("Chọn ổ khác…"); onClicked: gameDirRootPicker.open() }
                ActionButton {
                    primary: false; label: Tr.phrase("Mặc định"); visible: settingsBridge.defaultGameDirRoot !== ""
                    onClicked: settingsBridge.setDefaultGameDirRoot("")
                }
            }
            Text {
                id: gameDirRootErrorText
                objectName: "gameDirRootErrorText"
                visible: text.length > 0
                width: Math.min(parent.width, 720)
                wrapMode: Text.WordWrap
                color: Theme.danger
                font.pixelSize: Theme.fontBody
                lineHeight: 1.3
                Connections {
                    target: settingsBridge
                    function onGameDirRootError(message) { gameDirRootErrorText.text = message; }
                    function onGameDirRootChanged() { gameDirRootErrorText.text = ""; }
                }
            }
            Text {
                width: Math.min(parent.width, 720)
                wrapMode: Text.WordWrap
                text: Tr.phrase("Bản chơi mới (tạo mới, cài modpack, nhập file, kéo-thả) sẽ đặt mods/saves ở thư mục này; kho chung (versions, libraries, assets, Java) vẫn ở thư mục dữ liệu. Bản chơi đã có không bị chuyển.")
                color: Theme.textMuted; font.pixelSize: Theme.fontBody; lineHeight: 1.3
            }
            Rectangle { width: parent.width; height: 1; color: Theme.border }

            Text {
                width: Math.min(parent.width, 720)
                wrapMode: Text.WordWrap
                text: Tr.phrase("Thư viện mod và modpack duyệt CurseForge qua máy chủ của Nostalgia, không cần khoá API.")
                color: Theme.textMuted; font.pixelSize: Theme.fontBody; lineHeight: 1.3
            }
            Rectangle { width: parent.width; height: 1; color: Theme.border }
            Flow {
                width: parent.width
                spacing: 10
                Text { text: Tr.phrase("Âm thanh thông báo"); color: Theme.textMuted; font.pixelSize: Theme.fontBody; width: 210 * Theme.textScale
                        }
                Toggle {
                    objectName: "notificationSoundToggle"; accessibleLabel: Tr.phrase("Âm thanh thông báo")

                    checked: settingsBridge.notificationSound
                    onToggled: function (checked) { settingsBridge.setNotificationSound(checked); }
                }
                Text {

                    text: Tr.phrase("Chuông ngắn khi game khởi động, thoát, hoặc tải xong phiên bản.")
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody
                }
            }
            Flow {
                width: parent.width
                spacing: 10
                Text { text: Tr.phrase("Âm thanh giao diện"); color: Theme.textMuted; font.pixelSize: Theme.fontBody; width: 210 * Theme.textScale
                        }
                Toggle {
                    objectName: "uiSoundToggle"; accessibleLabel: Tr.phrase("Âm thanh giao diện")

                    checked: settingsBridge.uiSound
                    onToggled: function (checked) { settingsBridge.setUiSound(checked); }
                }
                Text {

                    text: Tr.phrase("Blip mềm kiểu Xbox 360 / Steam Big Picture khi chuyển trang, bấm nút, bung thẻ.")
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody
                }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.border }
            Flow {
                width: parent.width
                spacing: 10
                Text { text: Tr.phrase("Thu gọn vào khay khi chơi"); color: Theme.textMuted; font.pixelSize: Theme.fontBody; width: 210 * Theme.textScale
                        }
                Toggle {
                    objectName: "hideWhenGameRunningToggle"; accessibleLabel: Tr.phrase("Thu gọn vào khay khi chơi")

                    checked: settingsBridge.hideWhenGameRunning
                    onToggled: function (checked) { settingsBridge.setHideWhenGameRunning(checked); }
                }
                Text {

                    text: Tr.phrase("Ẩn cửa sổ launcher vào khay hệ thống khi game đang chạy, giải phóng RAM.")
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody
                }
            }
            Flow {
                width: parent.width
                spacing: 10
                Text { text: "Discord Rich Presence"; color: Theme.textMuted; font.pixelSize: Theme.fontBody; width: 210 * Theme.textScale
                        }
                Toggle {
                    objectName: "discordToggle"; accessibleLabel: Tr.phrase("Discord Rich Presence")

                    checked: settingsBridge.discordPresence
                    onToggled: function (checked) { settingsBridge.setDiscord(checked); }
                }
                Text {

                    text: presenceBridge.statusText
                    color: presenceBridge.connected ? Theme.accent : Theme.textMuted; font.pixelSize: Theme.fontBody
                }
            }
            Text {
                width: Math.min(parent.width, 720)
                wrapMode: Text.WordWrap
                text: Tr.phrase("Hồ sơ Discord của bạn hiện \"Đang ở launcher\", rồi \"Đang chơi <bản chơi>\" kèm thời gian khi game chạy. Không cần thiết lập gì: Discord mở lúc nào thì launcher tự nối lúc đó.")
                color: Theme.textMuted; font.pixelSize: Theme.fontBody; lineHeight: 1.3
            }
        }
    }

        }
    }

    FolderDialog {
        id: gameDirRootPicker
        title: Tr.phrase("Chọn thư mục lưu bản chơi mới")
        onAccepted: settingsBridge.setDefaultGameDirRoot(selectedFolder.toString())
    }
}
