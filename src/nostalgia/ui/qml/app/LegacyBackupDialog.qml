import QtQuick
import "../" as Legacy
import QtQuick.Dialogs

WorkspaceDialog {
    id: root
    objectName: "legacyBackupDialog"
    title: Legacy.Tr.phrase("Khôi phục dữ liệu cũ")
    guideTopic: "backup"
    description: Legacy.Tr.phrase("Giữ an toàn cho thế giới của bạn. Khôi phục từ bản sao lưu sẽ tạo một bản chơi mới.")
    busy: storageBridge.busy
    preferredWidth: 860
    property string selectedBackup: ""
    property string selectedLabel: ""
    property string statusMessage: ""
    property bool failed: false
    function openDialog() { statusMessage = ""; failed = false; selectedBackup = ""; selectedLabel = ""; restoreName.text = ""; storageBridge.refresh(); open(); notifier.playUi("open"); }
    function choose(path, label) { selectedBackup = path; selectedLabel = label; restoreName.text = "restore-" + Date.now(); statusMessage = ""; }
    Connections {
        target: storageBridge
        function onCompleted(message) { root.statusMessage = message; root.failed = false; }
        function onFailed(message) { root.statusMessage = message; root.failed = true; }
    }
    InertialScroll {
        objectName: "backupBodyScroll"
        anchors.fill: parent
        contentHeight: backupContent.implicitHeight + 8
        Column {
            id: backupContent
            width: parent.width - 10; spacing: 16
            Flow { width: parent.width; spacing: 8
                Button { label: Legacy.Tr.phrase("Mở thư mục sao lưu ↗"); quiet: true; onClicked: storageBridge.openBackupsFolder() }
                Button { objectName: "backupChooseFile"; label: Legacy.Tr.phrase("Chọn file sao lưu…"); clickable: !root.busy; onClicked: picker.open() }
            }
            PaymentText { text: Legacy.Tr.phrase("Bản sao lưu"); font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold }
            PaymentText { visible: !storageBridge.backups.length; width: parent.width; text: Legacy.Tr.phrase("Chưa có bản sao lưu. Mở quản lý một bản chơi → Sao lưu & dữ liệu để tạo bản sao gồm saves, mods và config."); color: GlassTheme.muted }
            Repeater {
                model: storageBridge.backups
                Button {
                    objectName: "backupRecord-" + index
                    width: backupContent.width; height: Math.max(54, GlassTheme.fontControl * 3)
                    label: modelData.label + " · " + modelData.created + " · " + modelData.size
                    selected: root.selectedBackup === modelData.path
                    clickable: !root.busy
                    onClicked: root.choose(modelData.path, modelData.label)
                }
            }
            PaymentText { text: Legacy.Tr.phrase("Thùng rác"); font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold }
            PaymentText { visible: !storageBridge.trash.length; width: parent.width; text: Legacy.Tr.phrase("Thùng rác trống. Bản chơi đã xoá có thể được đưa trở lại từ đây."); color: GlassTheme.muted }
            Repeater {
                model: storageBridge.trash
                Glass { width: backupContent.width; height: row.implicitHeight + 32; padding: 16; frosted: false
                    Row { id: row; width: parent.width; spacing: 12
                        PaymentText { width: parent.width - restoreTrash.width - purge.width - 24; anchors.verticalCenter: parent.verticalCenter; text: modelData.label; elide: Text.ElideRight; maximumLineCount: 1 }
                        Button { id: restoreTrash; objectName: "restoreTrash-" + index; label: Legacy.Tr.phrase("Khôi phục"); clickable: !root.busy; onClicked: storageBridge.restoreTrash(modelData.trashId) }
                        Button { id: purge; objectName: "purgeTrash-" + index; label: Legacy.Tr.phrase("Xóa hẳn"); quiet: true; danger: true; clickable: !root.busy; onClicked: { var trashId = modelData.trashId; confirmDialog.ask(Legacy.Tr.phrase("Xóa vĩnh viễn dữ liệu cũ?"), Legacy.Tr.phrase("Mods, cấu hình và thế giới trong bản chơi này sẽ bị xóa. Không thể hoàn tác."), function() { storageBridge.purgeTrash(trashId); }); } }
                    }
                }
            }
        }
    }
    footer: Column {
        width: root.bodyWidth; spacing: 10
        Rectangle { width: parent.width; height: 1; color: GlassTheme.stroke }
        PaymentText { objectName: "backupStatus"; width: parent.width; text: Legacy.Tr.message(root.statusMessage) || (root.busy ? Legacy.Tr.message(storageBridge.activity) : root.selectedBackup ? Legacy.Tr.phrase("Đã chọn: ") + root.selectedLabel : Legacy.Tr.phrase("Chọn bản sao lưu để khôi phục.")); color: root.failed ? GlassTheme.danger : GlassTheme.muted; font.pixelSize: GlassTheme.fontNote; maximumLineCount: 2; elide: Text.ElideRight }
        Flow { width: parent.width; spacing: 10
            Input { id: restoreName; objectName: "restoreName"; width: Math.min(260, root.bodyWidth); placeholder: Legacy.Tr.phrase("Mã bản chơi mới · restore-01") }
            Button { objectName: "restoreBackupButton"; primary: true; label: root.busy ? Legacy.Tr.phrase("Đang khôi phục…") : Legacy.Tr.phrase("Khôi phục sang bản mới"); clickable: !root.busy && !!root.selectedBackup && /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(restoreName.text); onClicked: storageBridge.restoreBackup(root.selectedBackup, restoreName.text) }
        }
    }
    FileDialog {
        id: picker; title: Legacy.Tr.phrase("Chọn bản sao lưu Nostalgia"); nameFilters: ["Nostalgia backup (*.zip)"]
        onAccepted: root.choose(String(selectedFile), String(selectedFile).split("/").pop())
    }
}
