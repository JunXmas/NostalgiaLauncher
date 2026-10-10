import QtQuick
import QtQuick.Controls as Controls
import "../" as Legacy

Controls.Popup {
    id: root
    objectName: "hostDialog"
    parent: Controls.Overlay.overlay
    width: Math.min(600, parent ? parent.width - 48 : 600)
    height: Math.min(heading.height + body.implicitHeight + footer.height + padding * 2 + 16,
        650 * GlassTheme.scale, parent ? parent.height - 48 : 650)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    padding: 24
    modal: true; dim: true; focus: true
    property Item backdrop: null
    readonly property var selectedInstance: bridge.instances[pack.currentIndex] || ({})
    property bool sharePack: false
    property bool directAllowed: true
    onSelectedInstanceChanged: hostBridge.modSelection.selectInstance(selectedInstance.instanceId || "")
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: GlassTheme.quick } }
    Controls.Overlay.modal: Rectangle { color: "#99080b12" }
    background: Glass {
        id: mica
        objectName: "hostDialogMica"
        padding: 0; radius: 22; color: "transparent"
        backdrop: root.backdrop
        backdropRect: {
            if (!root.backdrop || !root.parent) return Qt.rect(0, 0, 1, 1);
            var origin = root.parent.mapToItem(root.backdrop, root.x, root.y);
            return Qt.rect(origin.x, origin.y, root.width, root.height);
        }
        frosted: root.opened
        blurOpacity: 0.95; blurRadius: 64; finishOpacity: 0.45
        Rectangle {
            anchors.fill: parent; radius: mica.radius
            color: GlassTheme.alpha(GlassTheme.surface, mica.shaderAvailable ? 0.55 : 0.96)
            border.color: GlassTheme.alpha(GlassTheme.text, 0.14)
        }
    }
    Connections {
        target: hostBridge
        function onSetupRequested() {
            root.sharePack = hostBridge.syncAvailable;
            if (pack.currentIndex < 0 && pack.count) pack.currentIndex = 0;
            hostBridge.modSelection.selectInstance(root.selectedInstance.instanceId || "");
            root.open();
        }
    }
    contentItem: Item {
        id: dialogContent
        Item {
            id: heading
            width: parent.width; height: Math.max(hostTitle.implicitHeight, closeButton.height) + 12
            PaymentText { id: hostTitle; width: parent.width - closeButton.width - 12; text: Legacy.Tr.phrase("Tạo phòng chơi chung"); font.pixelSize: GlassTheme.fontDialog; font.weight: Font.DemiBold; font.family: GlassTheme.displayFont }
            Button { id: closeButton; anchors.right: parent.right; width: 36; height: 36; label: "×"; quiet: true; Accessible.name: Legacy.Tr.phrase("Đóng chọn bản chơi"); onClicked: root.close() }
        }
        InertialScroll {
            objectName: "hostSetupScroll"
            anchors.top: heading.bottom; anchors.left: parent.left; anchors.right: parent.right
            anchors.bottom: footer.top; anchors.bottomMargin: 16
            contentHeight: body.implicitHeight
            Column {
                id: body
                width: parent.width - 10; spacing: 14
                HostSteps { width: parent.width; currentStep: 0 }
                PaymentText { width: parent.width; text: Legacy.Tr.phrase("Tạo phòng chờ, mời bạn và đồng bộ modpack trước. Khi mọi người đã sẵn sàng, khởi chạy Minecraft và mở LAN."); color: GlassTheme.muted }
                PaymentText { text: Legacy.Tr.phrase("Bản chơi / modpack đã cài"); font.weight: Font.DemiBold }
                Select {
                    id: pack
                    objectName: "hostPackPicker"
                    width: parent.width
                    menuBackdrop: dialogContent.parent
                    model: bridge.instances.map(function (instance) { return instance.label; })
                }
                PaymentText {
                    objectName: "hostSelectedVersion"
                    width: parent.width
                    visible: !!root.selectedInstance.instanceId
                    text: (root.selectedInstance.versionId || "") + "  ·  " + (root.selectedInstance.modCount || 0) + " mod"
                    color: GlassTheme.brand; font.pixelSize: GlassTheme.fontCaption
                }
                Legacy.CheckRow {
                    objectName: "hostSharePack"
                    width: parent.width
                    label: Legacy.Tr.phrase("Đồng bộ modpack cho bạn bè · Plus")
                    checked: root.sharePack && hostBridge.syncAvailable
                    enabled: hostBridge.syncAvailable
                    opacity: enabled ? 1 : 0.5
                    onToggled: function (checked) { root.sharePack = checked; }
                }
                HostModList { visible: root.sharePack && hostBridge.syncAvailable; width: parent.width }
                Legacy.CheckRow {
                    objectName: "hostDirectAllowed"; width: parent.width
                    label: Legacy.Tr.phrase("Ưu tiên kết nối trực tiếp có mã hoá")
                    checked: root.directAllowed
                    onToggled: function(checked) { root.directAllowed = checked; }
                }
                PaymentText { width: parent.width; text: root.directAllowed ? Legacy.Tr.phrase("Kết nối trực tiếp có thể tiết lộ IP cho người cùng phòng. Nếu mạng chặn P2P, launcher dùng relay dự phòng.") : Legacy.Tr.phrase("Chỉ dùng relay để tránh chia sẻ IP trực tiếp với người cùng phòng."); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
                PaymentText {
                    width: parent.width
                    text: !plusFeaturesEnabled ? Legacy.Tr.phrase("Đồng bộ Plus đang tạm khóa. Bạn vẫn có thể mở phòng; mọi người cần dùng cùng modpack.")
                        : !hostBridge.syncAvailable ? Legacy.Tr.phrase("Host cần Plus để đồng bộ. Bạn bè nhận lời mời được tải bộ modpack miễn phí.")
                        : root.sharePack ? Legacy.Tr.phrase("Bộ modpack được chụp trước khi game chạy. Lời mời mở sau khi đồng bộ hoàn tất.")
                        : Legacy.Tr.phrase("Mọi người cần cài cùng phiên bản game, loader và mods trước khi vào phòng.")
                    color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption
                }
                PaymentText {
                    width: parent.width
                    text: !pack.count ? Legacy.Tr.phrase("Chưa có bản chơi. Cài modpack ở Thư viện hoặc tạo bản chơi trước.")
                        : bridge.gameRunning ? Legacy.Tr.phrase("Hãy đóng Minecraft đang chạy để host đúng bản chơi bạn chọn.")
                        : !bridge.activeAccountId ? Legacy.Tr.phrase("Bạn cần thêm tài khoản Minecraft trước khi chơi.")
                        : Legacy.Tr.message(hostBridge.details.note)
                    visible: !!text
                    color: GlassTheme.accent
                }
            }
        }
        Item {
            id: footer
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            height: launch.height
            GuideButton { topicId: "host"; anchors.left: parent.left }
            Button {
                id: launch
                objectName: "hostLaunchButton"
                anchors.right: parent.right
                label: Legacy.Tr.phrase("Tạo phòng"); primary: true
                clickable: !!root.selectedInstance.instanceId && !!bridge.activeAccountId && socialBridge.signedIn && !bridge.busy && !bridge.gameRunning && !bridge.storageBusy && !hostBridge.details.active && !multiplayerBridge.active && !roomSyncBridge.busy && !(root.sharePack && !hostBridge.modSelection.ready)
                onClicked: {
                    multiplayerBridge.setDirectAllowed(root.directAllowed);
                    if (hostBridge.createRoom(root.selectedInstance.instanceId, root.sharePack && hostBridge.syncAvailable)) root.close();
                }
            }
        }
    }
}
