import QtQuick

Item {
    id: root
    objectName: "dedicatedServers"
    function openCreate() { create.open(); }
    Glass {
        id: access
        width: parent.width; height: accessBody.implicitHeight + 36; padding: 18
        Column {
            id: accessBody
            width: parent.width; spacing: 12
            PaymentText { width: parent.width; text: "Một nơi để cùng chơi"; font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold; font.family: GlassTheme.displayFont }
            PaymentText { width: parent.width; text: "Pro · 6 tháng    /    Max · 1 năm    /    Ultimate · Vĩnh viễn"; color: GlassTheme.accent }
            PaymentText { width: parent.width; text: "Paper, Purpur, Folia, Fabric, Vanilla và Arclight hybrid. Chọn nền tảng, cài plugin/mod, chỉnh cấu hình và xem console tại đây."; color: GlassTheme.muted }
            Flow { width: parent.width; spacing: 12
                PaymentText { width: Math.max(200, parent.width - verify.width - 12); text: serverBridge.enabled ? serverBridge.note : "Host server trả phí đang tạm khoá. Server chạy trên máy bạn; không kèm VPS. Bạn có thể xem giao diện tạo server."; color: GlassTheme.muted }
                Button { id: verify; objectName: "serverVerifyAccess"; label: "Kiểm tra quyền"; visible: serverBridge.enabled && !serverBridge.hasAccess; clickable: !serverBridge.busy; onClicked: serverBridge.checkAccess() }
            }
        }
    }
    InertialScroll {
        objectName: "serversScroll"
        anchors.top: access.bottom; anchors.topMargin: 22
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        contentHeight: cards.implicitHeight + 20
        Column {
            id: cards
            width: parent.width - 8; spacing: 14
            Repeater {
                model: serverBridge.servers
                Glass {
                    width: cards.width; height: cardBody.implicitHeight + 36; padding: 18
                    Column {
                        id: cardBody
                        width: parent.width; spacing: 12
                        PaymentText { width: parent.width; text: modelData.display_name; font.pixelSize: GlassTheme.fontSubheading; font.weight: Font.DemiBold }
                        PaymentText { width: parent.width; text: modelData.engine_title + " · Minecraft " + modelData.game_version + " · " + modelData.heap_megabytes + " MB"; color: GlassTheme.muted }
                        Flow { width: parent.width; spacing: 10
                            Button { objectName: "serverManage-" + modelData.server_id; label: "Quản lý"; onClicked: manager.openFor(modelData.server_id) }
                            Button { objectName: "serverRun-" + modelData.server_id; label: serverBridge.runningId === modelData.server_id ? "Dừng & lưu thế giới" : "Khởi chạy"; primary: serverBridge.runningId !== modelData.server_id; clickable: !serverBridge.busy && (serverBridge.runningId === modelData.server_id || serverBridge.hasAccess && !serverBridge.runningId); onClicked: { if (serverBridge.runningId === modelData.server_id) serverBridge.stop(); else serverBridge.start(modelData.server_id); } }
                            PaymentText { text: serverBridge.readyId === modelData.server_id ? "● Sẵn sàng" : serverBridge.runningId === modelData.server_id ? "◌ Đang khởi động" : "○ Đã dừng"; color: serverBridge.runningId === modelData.server_id ? GlassTheme.accent : GlassTheme.muted }
                        }
                    }
                }
            }
            Glass {
                visible: serverBridge.servers.length === 0
                width: parent.width; height: emptyBody.implicitHeight + 48; padding: 24
                Column { id: emptyBody; width: parent.width; spacing: 12
                    PaymentText { width: parent.width; text: "Thế giới chung bắt đầu từ đây."; font.pixelSize: GlassTheme.fontSection; font.family: GlassTheme.displayFont }
                    PaymentText { width: parent.width; text: "Server giữ một thư mục riêng cho thế giới, plugin và mod. Game của bạn và dữ liệu bản chơi không bị dùng chung với server."; color: GlassTheme.muted }
                    Button { objectName: "serverCreateEmpty"; label: "Chọn nền tảng  +"; primary: true; onClicked: root.openCreate() }
                }
            }
        }
    }
    ServerCreateDialog { id: create }
    ServerManagerDialog { id: manager }
    Connections {
        target: serverBridge
        function onCreated(serverId) { create.close(); manager.openFor(serverId); }
    }
}
