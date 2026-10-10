import QtQuick

/*
  Mục CẬP NHẬT ở trang CÀI ĐẶT: phiên bản đang dùng, công tắc tự kiểm lúc khởi động, nút kiểm
  ngay, và theo trạng thái của `updateBridge`: ghi chú bản mới + Tải về → thanh tiến độ →
  "Cài và mở lại" (gói đóng sẵn) hoặc "Mở trang tải" (chạy từ mã nguồn).
*/
Panel {
    id: panel
    title: Tr.phrase("CẬP NHẬT")
    readonly property string state: updateBridge.state
    readonly property bool canSelfUpdate: updateBridge.canSelfUpdate
    implicitHeight: panel.contentTop + column.implicitHeight + Theme.pad
    height: implicitHeight

    Column {
        id: column
        width: parent.width
        spacing: 12
        Flow {
            width: parent.width
            spacing: 10
            Text { text: Tr.phrase("Đang dùng"); color: Theme.textMuted; font.pixelSize: Theme.fontBody; width: 210 * Theme.textScale
                    }
            Text { text: "v" + settingsBridge.launcherVersion; color: Theme.text; font.pixelSize: Theme.fontBody
                    }
            Item { width: 24; height: 1 }
            Toggle {
                objectName: "autoUpdateToggle"; accessibleLabel: Tr.phrase("Tự kiểm bản mới khi mở launcher")

                checked: settingsBridge.autoUpdateCheck
                onToggled: function (checked) { settingsBridge.setAutoUpdateCheck(checked); }
            }
            Text { text: Tr.phrase("Tự kiểm bản mới khi mở launcher"); color: Theme.textMuted; font.pixelSize: Theme.fontBody
                    }
        }
        Flow {
            width: parent.width
            spacing: 10
            ActionButton {
                objectName: "checkUpdateButton"
                primary: false
                label: panel.state === "checking" ? Tr.phrase("Đang kiểm...") : Tr.phrase("⟳  Kiểm tra bản mới")
                clickable: panel.state !== "checking" && panel.state !== "downloading"
                onClicked: updateBridge.checkNow()
            }
            ActionButton {
                objectName: "updateNowButton"
                visible: panel.state === "available"
                // Một nút cho cả việc: tải → tráo → mở lại (xem UpdateBanner.qml).
                label: panel.canSelfUpdate ? Tr.phrase("⬇  Cập nhật ngay") : Tr.phrase("Mở trang tải")
                onClicked: updateBridge.updateNow()
            }
            Text {
                objectName: "updateMessage"

                text: Tr.message(updateBridge.message)
                color: panel.state === "failed" ? Theme.danger
                       : panel.state === "available" || panel.state === "ready" ? Theme.accent : Theme.textMuted
                font.pixelSize: Theme.fontBody
            }
        }
        Rectangle {
            visible: panel.state === "downloading"
            width: Math.min(parent.width, 420); height: 4; radius: Theme.modern ? 8 : 0; color: Theme.border
            Rectangle {
                height: parent.height; radius: Theme.modern ? 8 : 0; color: Theme.accent
                width: parent.width * updateBridge.progressFraction
                Behavior on width { NumberAnimation { duration: Theme.quick } }
            }
        }
        Text {
            visible: (panel.state === "available" || panel.state === "ready") && updateBridge.releaseNotes.length > 0
            width: Math.min(parent.width, 720)
            wrapMode: Text.WordWrap; maximumLineCount: 6; elide: Text.ElideRight
            text: updateBridge.releaseNotes
            color: Theme.textMuted; font.pixelSize: Theme.fontBody; lineHeight: 1.3
        }
        Text {
            visible: !panel.canSelfUpdate
            width: Math.min(parent.width, 720)
            wrapMode: Text.WordWrap
            text: updateBridge.installKind === "app"
                  ? Tr.phrase("Gói macOS (.app): launcher chỉ báo có bản mới; tải .dmg mới từ trang release rồi kéo đè vào Applications.")
                  : Tr.phrase("Đang chạy từ mã nguồn: launcher chỉ báo có bản mới; cập nhật bằng git pull + uv sync. Gói đóng sẵn Linux/Windows (tải từ trang release) thì tự cài và mở lại.")
            color: Theme.textMuted; font.pixelSize: Theme.fontBody; lineHeight: 1.3
        }
    }
}
