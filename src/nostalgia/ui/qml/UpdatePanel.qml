import QtQuick

/*
  Mục CẬP NHẬT ở trang CÀI ĐẶT: phiên bản đang dùng, công tắc tự kiểm lúc khởi động, nút kiểm
  ngay, và theo trạng thái của `updateBridge`: ghi chú bản mới + Tải về → thanh tiến độ →
  "Cài và mở lại" (gói đóng sẵn) hoặc "Mở trang tải" (chạy từ mã nguồn).
*/
Panel {
    id: panel
    title: "CẬP NHẬT"
    readonly property string state: updateBridge.state
    readonly property bool frozen: updateBridge.installKind === "frozen"
    implicitHeight: panel.contentTop + column.implicitHeight + Theme.pad
    height: implicitHeight

    Column {
        id: column
        width: parent.width
        spacing: 12
        Row {
            spacing: 10
            Text { text: "Đang dùng"; color: Theme.textMuted; font.pixelSize: 12; width: 160
                   anchors.verticalCenter: parent.verticalCenter }
            Text { text: "v" + settingsBridge.launcherVersion; color: Theme.text; font.pixelSize: 12
                   anchors.verticalCenter: parent.verticalCenter }
            Item { width: 24; height: 1 }
            Toggle {
                objectName: "autoUpdateToggle"
                anchors.verticalCenter: parent.verticalCenter
                checked: settingsBridge.autoUpdateCheck
                onToggled: function (checked) { settingsBridge.setAutoUpdateCheck(checked); }
            }
            Text { text: "Tự kiểm bản mới khi mở launcher"; color: Theme.textMuted; font.pixelSize: 11
                   anchors.verticalCenter: parent.verticalCenter }
        }
        Row {
            spacing: 10
            ActionButton {
                objectName: "checkUpdateButton"
                primary: false
                label: panel.state === "checking" ? "Đang kiểm..." : "⟳  Kiểm tra bản mới"
                clickable: panel.state !== "checking" && panel.state !== "downloading"
                onClicked: updateBridge.checkNow()
            }
            ActionButton {
                objectName: "downloadUpdateButton"
                visible: panel.state === "available"
                label: "⬇  Tải bản " + updateBridge.latestVersion
                onClicked: updateBridge.download()
            }
            ActionButton {
                objectName: "applyUpdateButton"
                visible: panel.state === "ready"
                label: panel.frozen ? "Cài và mở lại" : "Mở trang tải"
                onClicked: panel.frozen ? updateBridge.applyAndRestart() : updateBridge.openReleasePage()
            }
            Text {
                objectName: "updateMessage"
                anchors.verticalCenter: parent.verticalCenter
                text: updateBridge.message
                color: panel.state === "failed" ? Theme.danger
                       : panel.state === "available" || panel.state === "ready" ? Theme.accent : Theme.textMuted
                font.pixelSize: 12
            }
        }
        Rectangle {
            visible: panel.state === "downloading"
            width: Math.min(parent.width, 420); height: 4; radius: 2; color: Theme.border
            Rectangle {
                height: parent.height; radius: 2; color: Theme.accent
                width: parent.width * updateBridge.progressFraction
                Behavior on width { NumberAnimation { duration: Theme.quick } }
            }
        }
        Text {
            visible: (panel.state === "available" || panel.state === "ready") && updateBridge.releaseNotes.length > 0
            width: Math.min(parent.width, 720)
            wrapMode: Text.WordWrap; maximumLineCount: 6; elide: Text.ElideRight
            text: updateBridge.releaseNotes
            color: Theme.textMuted; font.pixelSize: 11; lineHeight: 1.3
        }
        Text {
            visible: !panel.frozen
            width: Math.min(parent.width, 720)
            wrapMode: Text.WordWrap
            text: updateBridge.installKind === "app"
                  ? "Gói macOS (.app): launcher chỉ báo có bản mới; tải .dmg mới từ trang release rồi kéo đè vào Applications."
                  : "Đang chạy từ mã nguồn: launcher chỉ báo có bản mới; cập nhật bằng git pull + uv sync. Gói đóng sẵn Linux/Windows (tải từ trang release) thì tự cài và mở lại."
            color: Theme.textMuted; font.pixelSize: 11; lineHeight: 1.3
        }
    }
}
