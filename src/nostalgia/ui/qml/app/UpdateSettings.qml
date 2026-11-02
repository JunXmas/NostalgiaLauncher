import QtQuick
import "../" as Legacy

Glass {
    id: root
    objectName: "modernUpdateSettings"
    padding: 22
    implicitHeight: content.implicitHeight + padding * 2
    height: implicitHeight
    Column {
        id: content
        width: parent.width; spacing: 16
        PaymentText { text: Legacy.Tr.phrase("Luôn có điều mới."); font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontHeading; font.weight: Font.DemiBold }
        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Đang dùng ") + settingsBridge.launcherVersion + (updateBridge.latestVersion ? Legacy.Tr.phrase(" · Bản mới ") + updateBridge.latestVersion : ""); color: GlassTheme.muted }
        Flow {
            width: parent.width; spacing: 12
            Legacy.Toggle { objectName: "autoUpdateToggle"; accessibleLabel: Legacy.Tr.phrase("Tự kiểm bản mới khi mở launcher"); checked: settingsBridge.autoUpdateCheck; onToggled: function (checked) { settingsBridge.setAutoUpdateCheck(checked); } }
            PaymentText { text: Legacy.Tr.phrase("Tự kiểm bản mới khi mở launcher"); color: GlassTheme.muted }
        }
        PaymentText { objectName: "updateMessage"; width: parent.width; text: Legacy.Tr.message(updateBridge.message); color: updateBridge.state === "failed" ? GlassTheme.danger : GlassTheme.muted }
        Flow {
            width: parent.width; spacing: 10
            Button { objectName: "checkUpdateButton"; label: updateBridge.state === "checking" ? Legacy.Tr.phrase("Đang kiểm tra…") : Legacy.Tr.phrase("Kiểm tra bản mới"); clickable: ["checking","downloading","applying"].indexOf(updateBridge.state) < 0; onClicked: updateBridge.checkNow() }
            Button { objectName: "updateNowButton"; primary: true; label: Legacy.Tr.phrase("Xem bản cập nhật ↗"); visible: ["available","downloading","ready","applying","failed"].indexOf(updateBridge.state) >= 0; onClicked: details.open() }
        }
    }
    UpdateDialog { id: details; backdrop: Legacy.Theme.modalBackdrop }
}
