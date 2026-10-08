import QtQuick
import QtQuick.Controls as Controls

Controls.Popup {
    id: root
    objectName: "modernUpdateDialog"
    property Item backdrop: null
    readonly property string phase: typeof updateBridge !== "undefined" && updateBridge ? updateBridge.state : "idle"
    readonly property string latestVersion: typeof updateBridge !== "undefined" && updateBridge ? updateBridge.latestVersion : ""
    readonly property string notesText: typeof updateBridge !== "undefined" && updateBridge ? updateBridge.releaseNotes : ""
    readonly property string statusMessage: typeof updateBridge !== "undefined" && updateBridge ? updateBridge.message : ""
    readonly property real fraction: typeof updateBridge !== "undefined" && updateBridge ? updateBridge.progressFraction : 0
    readonly property bool selfUpdate: typeof updateBridge !== "undefined" && updateBridge ? updateBridge.canSelfUpdate : false
    readonly property bool working: ["checking", "downloading", "applying"].indexOf(phase) >= 0
    parent: Controls.Overlay.overlay
    width: Math.min(720 * Math.min(GlassTheme.scale, 1.15), parent ? parent.width - 40 : 720)
    height: Math.min(720, parent ? parent.height - 40 : 720)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    padding: 24
    modal: true; dim: true; focus: true
    closePolicy: Controls.Popup.CloseOnEscape
    enter: Transition { ParallelAnimation { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal } NumberAnimation { property: "scale"; from: GlassTheme.reducedMotion ? 1 : 0.98; to: 1; duration: GlassTheme.normal; easing.type: Easing.OutCubic } } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: GlassTheme.quick } }
    Controls.Overlay.modal: Rectangle { color: "#a8080b12" }
    background: Glass {
        id: mica
        objectName: "updateDialogMica"
        padding: 0; color: "transparent"
        backdrop: root.backdrop
        frosted: root.opened; blurOpacity: 0.92; blurRadius: 64; finishOpacity: 0.45
        backdropRect: { if (!root.backdrop || !root.parent) return Qt.rect(0,0,1,1); var p = root.parent.mapToItem(root.backdrop,root.x,root.y); return Qt.rect(p.x,p.y,root.width,root.height); }
        Rectangle { anchors.fill: parent; radius: mica.radius; color: GlassTheme.alpha(GlassTheme.surface, mica.shaderAvailable ? 0.60 : 0.97); border.color: GlassTheme.alpha(GlassTheme.text,0.14) }
    }
    contentItem: Item {
        Column {
            id: heading
            width: parent.width
            spacing: 12
            Row {
                width: parent.width; spacing: 16
                Column {
                    width: parent.width - closeButton.width - 16; spacing: 7
                    PaymentText { width: parent.width; text: "NOSTALGIA · CHUYẾN PHIÊU LƯU MỚI"; color: GlassTheme.accent; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
                    PaymentText { width: parent.width; text: root.phase === "failed" ? "Cần thử lại một chút." : root.phase === "upToDate" ? "Bạn đã có bản mới nhất." : "Một khởi đầu mới,\nvẫn là Nostalgia."; font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontDialog; font.weight: Font.DemiBold; lineHeight: 1.1 }
                }
                Button { id: closeButton; objectName: "updateDialogClose"; label: "×"; quiet: true; width: 36; onClicked: root.close() }
            }
            Flow {
                width: parent.width; spacing: 10
                PaymentText { text: "Đang dùng  " + settingsBridge.launcherVersion; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
                PaymentText { text: root.latestVersion ? "→  " + root.latestVersion : ""; color: GlassTheme.accent; font.pixelSize: GlassTheme.fontNote; font.weight: Font.DemiBold }
            }
            Rectangle { width: parent.width; height: 1; color: GlassTheme.stroke }
        }
        InertialScroll {
            id: notes
            objectName: "updateChangelogScroll"
            anchors.top: heading.bottom; anchors.topMargin: 16
            anchors.bottom: footer.top; anchors.bottomMargin: 18
            width: parent.width
            clip: true
            contentHeight: changelog.implicitHeight
            Text {
                id: changelog
                objectName: "updateChangelog"
                width: notes.width - 12
                text: root.notesText ? root.notesText.split("<details>")[0] : "Mỗi bản mới mang theo những sửa lỗi và cải thiện trải nghiệm. Kiểm tra phiên bản để xem có gì mới."
                textFormat: Text.MarkdownText; wrapMode: Text.WordWrap
                font.family: GlassTheme.font; font.pixelSize: GlassTheme.fontBody
                color: GlassTheme.text; linkColor: GlassTheme.accent; lineHeight: 1.35
                onLinkActivated: function (link) { if (link.startsWith("https://github.com/JunXmas/NostalgiaLauncher/")) Qt.openUrlExternally(link); }
            }
        }
        Column {
            id: footer
            anchors.bottom: parent.bottom
            width: parent.width
            spacing: 12
            PaymentText { objectName: "modernUpdateMessage"; width: parent.width; text: root.statusMessage; color: root.phase === "failed" ? GlassTheme.danger : GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
            Rectangle {
                visible: root.phase === "downloading"
                width: parent.width; height: 5; radius: 3; color: GlassTheme.stroke
                Rectangle { width: parent.width * Math.max(0,Math.min(1,root.fraction)); height: parent.height; radius: 3; color: GlassTheme.accent; Behavior on width { NumberAnimation { duration: GlassTheme.quick } } }
            }
            PaymentText { width: parent.width; text: root.selfUpdate ? "Gói được kiểm SHA-256 trước khi cài. Launcher sẽ mở lại sau khi cập nhật." : "Tải bộ cài phù hợp trên trang phát hành để cập nhật phiên bản này."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
            Flow {
                width: parent.width; spacing: 10
                Button { objectName: "modernUpdateNow"; primary: true; label: root.phase === "downloading" ? "Đang tải · " + Math.round(root.fraction * 100) + "%" : root.phase === "applying" ? "Đang cài…" : root.phase === "ready" ? "Cài & mở lại" : root.phase === "available" ? (root.selfUpdate ? "Cập nhật ngay →" : "Tải bản mới ↗") : "Kiểm tra bản mới"; clickable: !root.working; onClicked: { if (root.phase === "available") updateBridge.updateNow(); else if (root.phase === "ready") updateBridge.applyAndRestart(); else updateBridge.checkNow(); } }
                Button { label: "Để sau"; quiet: true; onClicked: root.close() }
            }
        }
    }
}
