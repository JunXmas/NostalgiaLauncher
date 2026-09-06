import QtQuick
import "../"

/* CÀI ĐẶT: thông tin chung. Không có tuỳ chọn nào cần người chơi cấu hình — thư viện CurseForge
   đi qua máy chủ của dự án, không cần khoá. */
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

    Panel {
        anchors { top: header.bottom; left: parent.left; right: parent.right; bottom: parent.bottom
                  margins: Theme.gap; topMargin: 6 }
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
        }
    }
}
