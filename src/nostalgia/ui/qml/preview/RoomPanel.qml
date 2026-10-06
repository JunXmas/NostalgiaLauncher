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
            text: multiplayerBridge.role === "hosting" ? "●  Phòng đang mở · " + multiplayerBridge.joinerCount + " kết nối"
                : multiplayerBridge.role === "waiting_world" ? "Mở LAN trong Minecraft để bắt đầu"
                : multiplayerBridge.role === "joined" ? "●  Đã vào phòng của bạn" : "Chơi chung"
            color: multiplayerBridge.role === "hosting" || multiplayerBridge.role === "joined" ? GlassTheme.brand : GlassTheme.text
            font.weight: Font.DemiBold
        }
        PaymentText {
            width: parent.width
            visible: multiplayerBridge.role === "waiting_world" || root.detailsExpanded
            text: multiplayerBridge.role === "joined" ? "Trong game → Multiplayer → Kết nối trực tiếp. Dùng địa chỉ bên dưới nếu không thấy LAN."
                : multiplayerBridge.role === "hosting" ? "Chọn bạn rồi bấm Mời chơi. Giữ Minecraft và launcher mở khi chơi."
                : "Trong thế giới → Esc → Open to LAN → Start LAN World."
            color: GlassTheme.muted
        }
        Flow {
            width: parent.width; spacing: 8
            Button { objectName: "socialStopRoom"; label: multiplayerBridge.role === "waiting_world" ? "Huỷ" : "Rời phòng"; quiet: true; onClicked: multiplayerBridge.stop() }
            Button { visible: multiplayerBridge.role === "waiting_world"; objectName: "showManualLan"; label: root.manualExpanded ? "Thu gọn  ↑" : "Không tìm thấy LAN?"; quiet: true; onClicked: root.manualExpanded = !root.manualExpanded }
            Button { visible: multiplayerBridge.role !== "waiting_world"; objectName: "showRoomOptions"; label: root.detailsExpanded ? "Thu gọn  ↑" : "Tùy chọn phòng  ↓"; quiet: true; onClicked: root.detailsExpanded = !root.detailsExpanded }
            Button { visible: multiplayerBridge.role === "hosting"; label: root.sharingExpanded ? "Thu gọn modpack" : "Đồng bộ modpack · Plus"; onClicked: root.sharingExpanded = !root.sharingExpanded }
        }
        Flow {
            width: parent.width; spacing: 8
            visible: root.detailsExpanded
            Button { visible: multiplayerBridge.role === "joined"; label: "Chép 127.0.0.1:" + multiplayerBridge.localPort; onClicked: multiplayerBridge.copyLocalAddress() }
            Button { visible: multiplayerBridge.role === "hosting"; label: multiplayerBridge.locked ? "Mở khoá phòng" : "Khoá nhận khách mới"; quiet: true; onClicked: multiplayerBridge.setLocked(!multiplayerBridge.locked) }
        }
        Column {
            visible: multiplayerBridge.role === "waiting_world" && root.manualExpanded
            width: parent.width; spacing: 8
            PaymentText { width: parent.width; text: "Nhập cổng vừa được Minecraft báo (ví dụ 51234)."; color: GlassTheme.muted }
            Input { id: lanPort; objectName: "manualLanPort"; width: parent.width; placeholder: "Cổng LAN"; onAccepted: multiplayerBridge.supplyLanPort(text) }
            Button { objectName: "confirmLanPort"; label: "Kiểm tra và mở phòng"; clickable: !!lanPort.text; onClicked: multiplayerBridge.supplyLanPort(lanPort.text) }
        }
        Loader {
            width: parent.width
            active: (multiplayerBridge.role === "hosting" && root.sharingExpanded) || (multiplayerBridge.role === "joined" && !!roomSyncBridge.offer.name)
            sourceComponent: Component { Legacy.RoomSyncCard { width: parent.width; hostMode: multiplayerBridge.role === "hosting" } }
            height: item ? item.implicitHeight : 0
        }
    }
}
