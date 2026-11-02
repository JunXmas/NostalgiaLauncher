import QtQuick
import "../" as Legacy

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
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("Một nơi để cùng chơi"); font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold; font.family: GlassTheme.displayFont }
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("Miễn phí"); color: GlassTheme.accent }
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("Server chạy trên máy bạn · Paper, Purpur, Folia, Fabric và hybrid."); color: GlassTheme.muted }
            GuideButton { topicId: "server" }
            PaymentText { width: parent.width; text: Legacy.Tr.message(serverBridge.note); color: GlassTheme.muted }
        }
    }
    InertialScroll {
        objectName: "serversScroll"
        anchors.top: access.bottom; anchors.topMargin: 22
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        contentHeight: cards.implicitHeight + 20
        Flow {
            id: cards
            width: parent.width - 8; spacing: 14
            Repeater {
                model: serverBridge.servers
                Glass {
                    width: cards.width > 760 * GlassTheme.scale ? (cards.width - 14) / 2 : cards.width; height: cardBody.implicitHeight + 36; padding: 18
                    Column {
                        id: cardBody
                        width: parent.width; spacing: 12
                        PaymentText { width: parent.width; text: modelData.display_name; font.pixelSize: GlassTheme.fontSubheading; font.weight: Font.DemiBold }
                        PaymentText { width: parent.width; text: modelData.engine_title + " · Minecraft " + modelData.game_version + " · " + modelData.heap_megabytes + " MB"; color: GlassTheme.muted }
                        Flow { width: parent.width; spacing: 10
                            Button { objectName: "serverManage-" + modelData.server_id; label: Legacy.Tr.phrase("Quản lý"); onClicked: manager.openFor(modelData.server_id) }
                            Button { objectName: "serverRun-" + modelData.server_id; label: serverBridge.runningId === modelData.server_id ? Legacy.Tr.phrase("Dừng & lưu thế giới") : Legacy.Tr.phrase("Khởi chạy"); primary: serverBridge.runningId !== modelData.server_id; clickable: !serverBridge.busy && (serverBridge.runningId === modelData.server_id || !serverBridge.runningId); onClicked: { if (serverBridge.runningId === modelData.server_id) serverBridge.stop(); else serverBridge.start(modelData.server_id); } }
                            Button { objectName: "serverDelete-" + modelData.server_id; label: Legacy.Tr.phrase("Xoá"); danger: true; quiet: true; clickable: !serverBridge.busy && !serverBridge.runningId; onClicked: { var serverId = modelData.server_id; confirmDialog.ask(Legacy.Tr.phrase("Chuyển server vào thùng rác?"), Legacy.Tr.phrase("Thế giới, plugin và mod được giữ trong servers/.trash."), function() { serverBridge.trash(serverId); }); } }
                            PaymentText { text: serverBridge.readyId === modelData.server_id ? Legacy.Tr.phrase("● Sẵn sàng") : serverBridge.runningId === modelData.server_id ? Legacy.Tr.phrase("◌ Đang khởi động") : Legacy.Tr.phrase("○ Đã dừng"); color: serverBridge.runningId === modelData.server_id ? GlassTheme.accent : GlassTheme.muted }
                        }
                    }
                }
            }
            Glass {
                visible: serverBridge.servers.length === 0
                width: parent.width; height: emptyBody.implicitHeight + 48; padding: 24
                Column { id: emptyBody; width: parent.width; spacing: 12
                    PaymentText { width: parent.width; text: Legacy.Tr.phrase("Thế giới chung bắt đầu từ đây."); font.pixelSize: GlassTheme.fontSection; font.family: GlassTheme.displayFont }
                    PaymentText { width: parent.width; text: Legacy.Tr.phrase("Server giữ một thư mục riêng cho thế giới, plugin và mod. Game của bạn và dữ liệu bản chơi không bị dùng chung với server."); color: GlassTheme.muted }
                    Button { objectName: "serverCreateEmpty"; label: Legacy.Tr.phrase("Chọn nền tảng  +"); primary: true; onClicked: root.openCreate() }
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
