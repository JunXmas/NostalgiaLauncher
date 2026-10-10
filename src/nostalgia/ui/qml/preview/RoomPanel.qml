import QtQuick
import "../" as Legacy

Glass {
    id: root
    objectName: "socialRoomPanel"
    property bool detailsExpanded: false
    property bool sharingExpanded: false
    property bool manualExpanded: false
    padding: 16
    implicitHeight: contents.implicitHeight + 32
    height: implicitHeight
    Column {
        id: contents
        width: parent.width; spacing: 10
        PaymentText {
            width: parent.width
            text: hostBridge.details.active ? hostBridge.details.label
                : multiplayerBridge.role === "hosting" ? Legacy.Tr.phrase("●  Phòng đang mở · ") + multiplayerBridge.joinerCount + Legacy.Tr.plural(" kết nối", multiplayerBridge.joinerCount)
                : multiplayerBridge.role === "waiting_world" ? Legacy.Tr.phrase("Mở LAN trong Minecraft để bắt đầu")
                : multiplayerBridge.role === "joined" ? Legacy.Tr.phrase("●  Đã vào phòng của bạn") : Legacy.Tr.phrase("Chơi chung")
            color: multiplayerBridge.role === "hosting" || multiplayerBridge.role === "joined" ? GlassTheme.brand : GlassTheme.text
            font.weight: Font.DemiBold
        }
        PaymentText {
            objectName: "hostProgressNote"
            width: parent.width
            visible: hostBridge.details.active
            text: Legacy.Tr.message(hostBridge.details.note) + (hostBridge.details.stage === "ready" ? " · " + multiplayerBridge.joinerCount + Legacy.Tr.plural(" kết nối", multiplayerBridge.joinerCount) : "")
            color: hostBridge.details.stage === "error" ? GlassTheme.danger : GlassTheme.muted
        }
        PaymentText {
            width: parent.width
            visible: !hostBridge.details.active && (multiplayerBridge.role === "waiting_world" || root.detailsExpanded)
            text: multiplayerBridge.role === "joined" ? Legacy.Tr.phrase("Trong game → Multiplayer → Kết nối trực tiếp. Dùng địa chỉ bên dưới nếu không thấy LAN.")
                : multiplayerBridge.role === "hosting" ? Legacy.Tr.phrase("Chọn bạn rồi bấm Mời chơi. Giữ Minecraft và launcher mở khi chơi.")
                : Legacy.Tr.phrase("Trong thế giới → Esc → Open to LAN → Start LAN World.")
            color: GlassTheme.muted
        }
        Flow {
            width: parent.width; spacing: 8
            Button { objectName: "socialStopRoom"; label: hostBridge.details.active && hostBridge.details.stage !== "ready" || multiplayerBridge.role === "waiting_world" ? Legacy.Tr.phrase("Huỷ") : Legacy.Tr.phrase("Rời phòng"); quiet: true; onClicked: { if (hostBridge.details.active) hostBridge.stop(); else multiplayerBridge.stop(); } }
            Button { objectName: "hostRetryShare"; visible: hostBridge.details.active && hostBridge.details.stage === "error"; label: Legacy.Tr.phrase("Thử đồng bộ lại"); clickable: !roomSyncBridge.busy; onClicked: hostBridge.retryShare() }
            Button { visible: multiplayerBridge.role === "waiting_world"; objectName: "showManualLan"; label: root.manualExpanded ? Legacy.Tr.phrase("Thu gọn  ↑") : Legacy.Tr.phrase("Không tìm thấy LAN?"); quiet: true; onClicked: root.manualExpanded = !root.manualExpanded }
            Button { visible: roomSyncBridge.hostReady && multiplayerBridge.role !== "waiting_world" && multiplayerBridge.active; objectName: "showRoomOptions"; label: root.detailsExpanded ? Legacy.Tr.phrase("Thu gọn  ↑") : Legacy.Tr.phrase("Tùy chọn phòng  ↓"); quiet: true; onClicked: root.detailsExpanded = !root.detailsExpanded }
            Button { visible: !hostBridge.details.active && plusFeaturesEnabled && multiplayerBridge.role === "hosting"; label: root.sharingExpanded ? Legacy.Tr.phrase("Thu gọn modpack") : Legacy.Tr.phrase("Đồng bộ modpack · Plus"); onClicked: root.sharingExpanded = !root.sharingExpanded }
        }
        Flow {
            width: parent.width; spacing: 8
            visible: root.detailsExpanded && roomSyncBridge.hostReady
            Button { visible: multiplayerBridge.role === "joined"; label: Legacy.Tr.phrase("Chép 127.0.0.1:") + multiplayerBridge.localPort; onClicked: multiplayerBridge.copyLocalAddress() }
            Button { visible: multiplayerBridge.role === "hosting"; label: multiplayerBridge.locked ? Legacy.Tr.phrase("Mở khoá phòng") : Legacy.Tr.phrase("Khoá nhận khách mới"); quiet: true; onClicked: multiplayerBridge.setLocked(!multiplayerBridge.locked) }
        }
        Column {
            visible: multiplayerBridge.role === "waiting_world" && root.manualExpanded
            width: parent.width; spacing: 8
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("Nhập cổng vừa được Minecraft báo (ví dụ 51234)."); color: GlassTheme.muted }
            Input { id: lanPort; objectName: "manualLanPort"; width: parent.width; placeholder: Legacy.Tr.phrase("Cổng LAN"); onAccepted: multiplayerBridge.supplyLanPort(text) }
            Button { objectName: "confirmLanPort"; label: Legacy.Tr.phrase("Kiểm tra và mở phòng"); clickable: !!lanPort.text; onClicked: multiplayerBridge.supplyLanPort(lanPort.text) }
        }
        Loader {
            width: parent.width
            active: plusFeaturesEnabled && ((!hostBridge.details.active && multiplayerBridge.role === "hosting" && root.sharingExpanded) || (multiplayerBridge.role === "joined" && !!roomSyncBridge.offer.name))
            sourceComponent: Component { Legacy.RoomSyncCard { width: parent.width; hostMode: multiplayerBridge.role === "hosting" } }
            height: item ? item.implicitHeight : 0
        }
    }
}
