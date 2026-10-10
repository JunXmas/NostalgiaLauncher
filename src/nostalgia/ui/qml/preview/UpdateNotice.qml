import QtQuick
import "../" as Legacy

Glass {
    id: root
    objectName: "modernUpdateNotice"
    property string dismissedVersion: ""
    readonly property string phase: typeof updateBridge !== "undefined" && updateBridge ? updateBridge.state : "idle"
    readonly property string latestVersion: typeof updateBridge !== "undefined" && updateBridge ? updateBridge.latestVersion : ""
    readonly property real fraction: typeof updateBridge !== "undefined" && updateBridge ? updateBridge.progressFraction : 0
    readonly property bool active: typeof updateBridge !== "undefined" && !!updateBridge && root.latestVersion !== dismissedVersion && ["available", "downloading", "ready", "applying"].indexOf(root.phase) >= 0
    signal detailsRequested
    visible: active
    padding: 18
    width: Math.min(400 * GlassTheme.scale, parent ? parent.width - 48 : 400)
    height: contents.implicitHeight + padding * 2
    frosted: visible
    opacity: active ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: GlassTheme.normal } }
    Column {
        id: contents
        width: parent.width
        spacing: 12
        Row {
            width: parent.width
            spacing: 12
            Column {
                width: parent.width - dismiss.width - 12
                spacing: 4
                PaymentText { width: parent.width; text: Legacy.Tr.phrase("NOSTALGIA · CẬP NHẬT"); color: GlassTheme.accent; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
                PaymentText { width: parent.width; text: root.phase === "downloading" ? Legacy.Tr.phrase("Đang tải bản ") + root.latestVersion : root.phase === "applying" || root.phase === "ready" ? Legacy.Tr.phrase("Sắp mở lại với bản mới") : Legacy.Tr.phrase("Có điều mới đang chờ bạn."); font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontHeading; font.weight: Font.DemiBold }
            }
            Button { id: dismiss; objectName: "modernUpdateDismiss"; label: "×"; quiet: true; width: 34; height: 34; onClicked: root.dismissedVersion = root.latestVersion }
        }
        Rectangle {
            width: parent.width; height: 3; radius: 2
            visible: root.phase === "downloading"
            color: GlassTheme.stroke
            Rectangle { width: parent.width * Math.max(0, Math.min(1, root.fraction)); height: parent.height; radius: 2; color: GlassTheme.accent; Behavior on width { NumberAnimation { duration: GlassTheme.quick } } }
        }
        Row {
            width: parent.width
            spacing: 12
            PaymentText { width: parent.width - details.width - 12; anchors.verticalCenter: parent.verticalCenter; text: root.phase === "downloading" ? Math.round(root.fraction * 100) + Legacy.Tr.phrase("% · Đang kiểm toàn vẹn gói") : Legacy.Tr.phrase("Phiên bản ") + root.latestVersion; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
            Button { id: details; objectName: "modernUpdateDetails"; label: Legacy.Tr.phrase("Xem chi tiết ↗"); primary: true; onClicked: root.detailsRequested() }
        }
    }
}
