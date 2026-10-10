import QtQuick
import QtQuick.Controls as Controls
import "../" as Legacy

Controls.Popup {
    id: root
    objectName: "guestSyncDialog"
    parent: Controls.Overlay.overlay
    property Item backdrop: null
    property bool acknowledged: false
    property string kind: "mods"
    readonly property var rows: roomSyncBridge.guestChoices.filter(function(choice) {
        return choice.kind === root.kind && (!query.text.length || (choice.title + " " + choice.path).toLowerCase().indexOf(query.text.toLowerCase()) >= 0);
    })
    width: Math.min(700 * GlassTheme.scale, parent ? parent.width - 48 : 700)
    height: Math.min(760 * GlassTheme.scale, parent ? parent.height - 48 : 760)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    modal: true; dim: true; focus: true; padding: 24
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: GlassTheme.quick } }
    Controls.Overlay.modal: Rectangle { color: "#99080b12" }
    Connections {
        target: roomSyncBridge
        function onReviewRequested() { root.acknowledged = false; root.kind = "mods"; query.text = ""; root.open(); }
        function onReviewChanged() { if (!roomSyncBridge.reviewReady) { root.acknowledged = false; root.close(); } }
    }
    background: Glass {
        id: mica
        objectName: "guestSyncDialogMica"
        padding: 0; radius: 22; color: "transparent"
        backdrop: root.backdrop
        backdropRect: {
            if (!root.backdrop || !root.parent) return Qt.rect(0, 0, 1, 1);
            var origin = root.parent.mapToItem(root.backdrop, root.x, root.y);
            return Qt.rect(origin.x, origin.y, root.width, root.height);
        }
        frosted: root.opened; blurRadius: 64; blurOpacity: 0.95; finishOpacity: 0.45
        Rectangle { anchors.fill: parent; radius: mica.radius; color: GlassTheme.alpha(GlassTheme.surface, mica.shaderAvailable ? 0.65 : 0.98); border.color: GlassTheme.stroke }
    }
    contentItem: Item {
        Item {
            id: heading
            width: parent.width; height: 72 * GlassTheme.scale
            PaymentText { width: parent.width - 44; text: roomSyncBridge.updateLabel ? Legacy.Tr.phrase("Cập nhật bản chơi") : Legacy.Tr.phrase("Nhận modpack từ bạn bè"); font.pixelSize: GlassTheme.fontDialog; font.family: GlassTheme.displayFont; font.weight: Font.DemiBold }
            PaymentText { y: 36 * GlassTheme.scale; width: parent.width - 44; wrapMode: Text.NoWrap; elide: Text.ElideRight; text: roomSyncBridge.updateLabel || roomSyncBridge.offer.name || ""; color: GlassTheme.brand }
            Button { anchors.right: parent.right; width: 36; height: 36; label: "×"; quiet: true; onClicked: root.close(); Accessible.name: Legacy.Tr.phrase("Đóng lựa chọn đồng bộ") }
        }
        InertialScroll {
            objectName: "guestSyncScroll"
            anchors.top: heading.bottom; anchors.bottom: footer.top; anchors.bottomMargin: 12
            anchors.left: parent.left; anchors.right: parent.right
            contentHeight: body.implicitHeight + 8
            Column {
                id: body
                width: parent.width - 10; spacing: 12
                GuideButton { topicId: "sync" }
                Rectangle {
                    width: parent.width; height: risk.implicitHeight + 24; radius: 14
                    color: GlassTheme.alpha(GlassTheme.accent, 0.12); border.color: GlassTheme.alpha(GlassTheme.accent, 0.25)
                    PaymentText {
                        id: risk; x: 12; y: 12; width: parent.width - 24
                        text: Legacy.Tr.phrase("Cảnh báo bảo mật\nMods là mã thực thi, có thể đọc file và chạy chương trình trên máy. Scripts và KubeJS cũng có thể chạy mã. Chỉ nhận từ host bạn tin tưởng. SHA-256 kiểm tra toàn vẹn, không phát hiện virus; tên, icon và nguồn hiển thị do host cung cấp.")
                        font.pixelSize: GlassTheme.fontBody; color: GlassTheme.text
                    }
                }
                PaymentText {
                    width: parent.width; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption
                    text: roomSyncBridge.updateLabel ? Legacy.Tr.phrase("Giữ thế giới và file khách tự thêm. Thay phần đã đồng bộ; file cũ được sao lưu. Nội dung mới mặc định chưa chọn. Host đổi phiên bản game có thể ảnh hưởng thế giới đã lưu.")
                        : Legacy.Tr.phrase("Tạo một bản chơi riêng. Có thể bỏ chọn mods, texture pack và shader pack. Cấu hình và scripts đi cùng pack; thiếu mod bắt buộc có thể khiến game không chạy hoặc không vào được phòng.")
                }
                MotionTabs {
                    width: parent.width; labels: ["Mods", "Texture pack", "Shader pack"]
                    namePrefix: "guestSyncTab-"
                    currentIndex: ["mods", "resourcepacks", "shaderpacks"].indexOf(root.kind)
                    onSelected: function(index) { root.kind = ["mods", "resourcepacks", "shaderpacks"][index]; query.text = ""; }
                }
                Input { id: query; width: parent.width; placeholder: Legacy.Tr.phrase("Tìm trong nội dung của host…"); maximumLength: 160 }
                Flow {
                    width: parent.width; spacing: 8
                    Button { label: Legacy.Tr.phrase("Chọn tất cả"); quiet: true; onClicked: roomSyncBridge.selectGuestAll(true, root.kind) }
                    Button { label: Legacy.Tr.phrase("Bỏ chọn"); quiet: true; onClicked: roomSyncBridge.selectGuestAll(false, root.kind) }
                    PaymentText { height: 36 * GlassTheme.scale; verticalAlignment: Text.AlignVCenter; text: root.rows.filter(function(choice) { return choice.selected; }).length + "/" + root.rows.length + Legacy.Tr.phrase(" đã chọn"); color: GlassTheme.muted }
                }
                InertialList {
                    id: choices
                    objectName: "guestSyncChoices"
                    width: parent.width; height: Math.min(count * (72 * GlassTheme.scale + spacing), 260 * GlassTheme.scale)
                    model: root.rows; clip: true; spacing: 8; boundsBehavior: Flickable.StopAtBounds

                    delegate: SyncContentRow {
                        required property var modelData
                        width: choices.width; content: modelData; selected: modelData.selected
                        interactive: !roomSyncBridge.busy
                        onToggled: function(selected) { roomSyncBridge.setGuestSelected(modelData.path, selected); }
                    }
                }
                PaymentText { visible: !root.rows.length; width: parent.width; text: Legacy.Tr.phrase("Không có nội dung phù hợp trong mục này."); color: GlassTheme.muted }
                PaymentText { width: parent.width; font.pixelSize: GlassTheme.fontCaption; color: GlassTheme.muted; text: Legacy.Tr.phrase("Texture pack được cài vào resourcepacks. Bạn bật pack muốn dùng trong Minecraft; tùy chọn cá nhân của bạn được giữ.") }
            }
        }
        Column {
            id: footer
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            spacing: 12
            Legacy.CheckRow { objectName: "guestSyncConsent"; width: parent.width; label: Legacy.Tr.phrase("Tôi tin tưởng host và hiểu rủi ro"); checked: root.acknowledged; onToggled: function(checked) { root.acknowledged = checked; } }
            Button {
                objectName: "guestSyncConfirm"
                width: parent.width; primary: true
                label: roomSyncBridge.updateLabel ? Legacy.Tr.phrase("Cập nhật bản chơi đã đồng bộ") : Legacy.Tr.phrase("Tạo bản chơi & đồng bộ")
                clickable: root.acknowledged && roomSyncBridge.reviewReady && !roomSyncBridge.busy && !bridge.busy && !bridge.gameRunning && !bridge.storageBusy
                onClicked: { if (roomSyncBridge.confirmSync(root.acknowledged)) root.close(); }
            }
        }
    }
}
