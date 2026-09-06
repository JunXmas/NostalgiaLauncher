import QtQuick
import "../"

/* CÀI ĐẶT: hiện chỉ có khoá API CurseForge (tuỳ chọn). Không có khoá vẫn duyệt được CurseForge
   qua máy chủ của dự án; khoá riêng thì gọi thẳng api.curseforge.com, nhanh và không phụ thuộc. */
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
        title: "CURSEFORGE"

        Column {
            anchors { left: parent.left; right: parent.right }
            spacing: 12
            Text {
                width: Math.min(parent.width, 720)
                wrapMode: Text.WordWrap
                text: "Thư viện duyệt được CurseForge ngay, qua máy chủ của Nostalgia. "
                      + "Nếu bạn có khoá API riêng (xin miễn phí tại console.curseforge.com), dán vào đây: "
                      + "launcher sẽ gọi thẳng CurseForge, không phụ thuộc máy chủ trung gian. "
                      + "Khoá được lưu ở máy bạn với quyền chỉ mình bạn đọc, hoặc đặt qua biến môi trường "
                      + settingsBridge.curseforgeKeyEnvName + "."
                color: Theme.textMuted; font.pixelSize: 12; lineHeight: 1.3
            }
            Row {
                spacing: 8
                Rectangle {
                    width: 8; height: 8; radius: 4
                    anchors.verticalCenter: parent.verticalCenter
                    color: settingsBridge.hasCurseforgeKey ? Theme.accent : Theme.textMuted
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: settingsBridge.hasCurseforgeKey ? "Đang dùng khoá riêng của bạn" : "Chưa có khoá riêng — đang đi qua máy chủ Nostalgia"
                    color: Theme.text; font.pixelSize: 12
                }
            }
            Row {
                spacing: 8
                TextField {
                    id: keyField
                    objectName: "curseforgeKeyField"
                    width: 420
                    placeholder: settingsBridge.hasCurseforgeKey ? "Đã lưu khoá — dán khoá mới để thay" : "$2a$10$..."
                    onAccepted: page.saveKey()
                }
                ActionButton { label: "Lưu"; onClicked: page.saveKey() }
                ActionButton {
                    visible: settingsBridge.hasCurseforgeKey
                    primary: false; label: "Xoá khoá"
                    onClicked: { settingsBridge.saveCurseforgeKey(""); keyField.text = ""; }
                }
            }
        }
    }

    function saveKey() {
        if (!keyField.text.trim()) return;
        settingsBridge.saveCurseforgeKey(keyField.text);
        keyField.text = "";
    }
}
