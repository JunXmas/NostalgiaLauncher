import QtQuick
import QtQuick.Controls as Controls

Column {
    id: root
    property var selection: hostBridge.modSelection
    width: parent.width
    spacing: 10
    PaymentText { text: "Mod chia sẻ · " + root.selection.selectedCount + "/" + root.selection.mods.length; font.weight: Font.DemiBold }
    Row {
        spacing: 8
        Button { label: "Chọn tất cả"; quiet: true; clickable: root.selection.ready; onClicked: root.selection.selectAll(true) }
        Button { label: "Bỏ chọn"; quiet: true; clickable: root.selection.ready; onClicked: root.selection.selectAll(false) }
    }
    PaymentText { width: parent.width; text: !root.selection.ready ? "Đang đọc danh sách mod… Nếu có lỗi, chọn lại bản chơi." : "Chỉ thay đổi bộ mod của bạn bè. Mod trên máy host giữ nguyên; cấu hình và gói tài nguyên vẫn đồng bộ. Giữ các mod bắt buộc để mọi người vào được thế giới."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
    ListView {
        objectName: "hostSharedModList"
        width: parent.width; height: Math.min(count * (72 * GlassTheme.scale + spacing), 240 * GlassTheme.scale)
        clip: true; spacing: 6; boundsBehavior: Flickable.StopAtBounds
        Controls.ScrollBar.vertical: Controls.ScrollBar { }
        model: root.selection.mods
        delegate: SyncContentRow {
            required property var modelData
            selectionName: "shareMod_" + modelData.fileName
            width: root.width; content: modelData; selected: modelData.shared
            interactive: root.selection.ready
            onToggled: function(checked) { root.selection.setShared(modelData.path, checked); }
        }
    }

    PaymentText { width: parent.width; visible: root.selection.ready && !root.selection.mods.length; text: "Không có file mod trong bản chơi này."; color: GlassTheme.muted }
}
