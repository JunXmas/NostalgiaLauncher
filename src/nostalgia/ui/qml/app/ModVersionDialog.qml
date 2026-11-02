import QtQuick
import "../" as Legacy

WorkspaceDialog {
    id: root
    objectName: "modVersionDialog"
    readonly property var details: modVersionBridge.details
    title: Legacy.Tr.phrase("Phiên bản mod")
    description: details.fileName || ""
    preferredWidth: 760 * GlassTheme.scale
    preferredHeight: 650 * GlassTheme.scale
    Connections {
        target: modVersionBridge
        function onOpened() { root.open(); }
        function onDismissed() { root.close(); }
    }
    Column {
        anchors.fill: parent
        spacing: 12
        PaymentText {
            id: note
            objectName: "modVersionNote"
            width: parent.width
            text: modVersionBridge.busy ? Legacy.Tr.phrase("Đang xử lý…") : Legacy.Tr.message(root.details.note)
            visible: !!text
            color: GlassTheme.accent
        }
        PaymentText {
            id: explanation
            width: parent.width
            text: bridge.gameRunning ? Legacy.Tr.phrase("Tắt game để đổi phiên bản mod.") : Legacy.Tr.phrase("Chỉ hiện bản tương thích với Minecraft và loader. Giữ bộ mod trước thay đổi để hoàn tác.")
            color: GlassTheme.muted
        }
        InertialList {
            width: parent.width
            height: Math.max(80, parent.height - note.height - explanation.height - 28)
            spacing: 8
            model: root.details.versions || []
            delegate: Glass {
                required property var modelData
                width: ListView.view.width - 8
                height: 72 * GlassTheme.scale
                padding: 12
                Column {
                    width: parent.width - choose.width - 12
                    spacing: 6
                    PaymentText { width: parent.width; text: modelData.number; font.weight: Font.DemiBold }
                    PaymentText { width: parent.width; text: modelData.type + " · " + modelData.published; color: GlassTheme.muted }
                }
                Button {
                    id: choose
                    objectName: "modVersion-" + modelData.versionId
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    label: modelData.current ? Legacy.Tr.phrase("Đang dùng") : Legacy.Tr.phrase("Dùng bản này")
                    clickable: !modelData.current && !modVersionBridge.busy && !bridge.gameRunning && !bridge.storageBusy
                    onClicked: modVersionBridge.apply(modelData.versionId)
                }
            }
            footer: PaymentText {
                width: parent.width
                visible: !modVersionBridge.busy && !(root.details.versions || []).length
                text: Legacy.Tr.phrase("Không có phiên bản tương thích để hiển thị.")
                color: GlassTheme.muted
            }
        }
    }
    footer: Row {
        spacing: 10
        Button { objectName: "modVersionUndo"; visible: !!root.details.canUndo; label: Legacy.Tr.phrase("Hoàn tác lần đổi gần nhất"); clickable: !modVersionBridge.busy && !bridge.gameRunning && !bridge.storageBusy; onClicked: modVersionBridge.undo() }
        Button { label: Legacy.Tr.phrase("Đóng"); quiet: true; onClicked: root.close() }
    }
}
