import QtQuick
import "../" as Legacy

Glass {
    id: root
    objectName: "socialRoomPanel"
    property bool detailsExpanded: false
    property bool sharingExpanded: false
    property bool manualExpanded: false
    readonly property bool isHost: hostBridge.details.active || multiplayerBridge.role === "hosting" || multiplayerBridge.role === "waiting_world"
    readonly property bool readyToInvite: (multiplayerBridge.role === "hosting" || multiplayerBridge.role === "waiting_world") && roomSyncBridge.hostReady && !!multiplayerBridge.roomCode
    readonly property string stage: hostBridge.details.active ? hostBridge.details.stage : multiplayerBridge.role
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
                : multiplayerBridge.role === "waiting_world" ? Legacy.Tr.phrase("Phòng chờ đã mở")
                : multiplayerBridge.role === "joined" ? Legacy.Tr.phrase("●  Đã vào phòng của bạn") : Legacy.Tr.phrase("Chơi chung")
            color: multiplayerBridge.role === "hosting" || multiplayerBridge.role === "joined" ? GlassTheme.brand : GlassTheme.text
            font.weight: Font.DemiBold
        }
        HostSteps { objectName: "hostRoomSteps"; width: parent.width; visible: root.isHost; currentStep: root.stage === "preparing" ? 0 : root.stage === "lobby" || root.stage === "publishing" ? 1 : 2 }
        PaymentText {
            objectName: "hostProgressNote"
            width: parent.width
            visible: hostBridge.details.active && root.stage !== "waiting_world"
            text: Legacy.Tr.message(hostBridge.details.note) + (hostBridge.details.stage === "ready" ? " · " + multiplayerBridge.joinerCount + Legacy.Tr.plural(" kết nối", multiplayerBridge.joinerCount) : "")
            color: hostBridge.details.stage === "error" ? GlassTheme.danger : GlassTheme.muted
        }
        PaymentText {
            width: parent.width
            visible: multiplayerBridge.role === "joined" || multiplayerBridge.role === "hosting" || multiplayerBridge.role === "waiting_world"
            text: multiplayerBridge.role === "joined" ? (multiplayerBridge.worldReady ? Legacy.Tr.phrase("World đã mở. Khởi chạy đúng bản chơi bên dưới để vào cùng bạn.") : Legacy.Tr.phrase("Bạn đã vào room. Đồng bộ modpack trong lúc chờ host mở world."))
                : root.stage === "lobby" ? Legacy.Tr.phrase("Mời bạn vào room và đồng bộ trước. Bấm Khởi chạy Minecraft khi bạn muốn mở world.")
                : root.readyToInvite ? Legacy.Tr.phrase("Phòng sẵn sàng. Mời bạn bên dưới và giữ Minecraft cùng launcher mở khi chơi.")
                : root.stage === "waiting_world" ? Legacy.Tr.phrase("Bước tiếp theo nằm trong Minecraft: mở world của bạn, rồi bật LAN.")
                : Legacy.Tr.phrase("Launcher đang chuẩn bị phòng. Nút mời sẽ xuất hiện khi world và modpack sẵn sàng.")
            color: GlassTheme.muted
        }
        Rectangle {
            objectName: "hostLanInstruction"
            visible: root.stage === "waiting_world"
            width: parent.width; height: lanGuide.implicitHeight + 24; radius: 12
            color: GlassTheme.alpha(GlassTheme.accent, 0.10)
            border.color: GlassTheme.alpha(GlassTheme.accent, 0.25)
            Column {
                id: lanGuide
                x: 12; y: 12; width: parent.width - 24; spacing: 8
                PaymentText { width: parent.width; text: "Esc → Open to LAN → Start LAN World"; font.weight: Font.DemiBold; font.pixelSize: GlassTheme.fontSubheading }
                PaymentText { width: parent.width; text: Legacy.Tr.phrase("Sau khi bật LAN, quay lại đây. Launcher tự phát hiện cổng; bạn không cần chép mã hay nhập cổng."); color: GlassTheme.muted }
            }
        }
        RoomInviteList { width: parent.width; visible: root.readyToInvite }
        Button { objectName: "launchLobbyGame"; visible: root.stage === "lobby" && roomSyncBridge.hostReady; label: Legacy.Tr.phrase("Khởi chạy Minecraft"); primary: true; onClicked: hostBridge.launchRoom() }
        GuestRoomActions { width: parent.width; visible: multiplayerBridge.role === "joined" }
        Flow {
            width: parent.width; spacing: 8
            GuideButton { topicId: "invite"; label: Legacy.Tr.phrase("Xem hướng dẫn có GIF") }
            Button { objectName: "socialStopRoom"; label: hostBridge.details.active && hostBridge.details.stage !== "ready" || multiplayerBridge.role === "waiting_world" ? Legacy.Tr.phrase("Huỷ") : Legacy.Tr.phrase("Rời phòng"); quiet: true; onClicked: { if (hostBridge.details.active) hostBridge.stop(); else multiplayerBridge.stop(); } }
            Button { objectName: "hostRetryShare"; visible: hostBridge.details.active && hostBridge.details.stage === "error"; label: Legacy.Tr.phrase("Thử đồng bộ lại"); clickable: !roomSyncBridge.busy; onClicked: hostBridge.retryShare() }
            Button { visible: root.stage === "waiting_world"; objectName: "showManualLan"; label: root.manualExpanded ? Legacy.Tr.phrase("Thu gọn  ↑") : Legacy.Tr.phrase("Không tìm thấy LAN?"); quiet: true; onClicked: root.manualExpanded = !root.manualExpanded }
            Button { visible: roomSyncBridge.hostReady && multiplayerBridge.role !== "waiting_world" && multiplayerBridge.active; objectName: "showRoomOptions"; label: root.detailsExpanded ? Legacy.Tr.phrase("Thu gọn  ↑") : Legacy.Tr.phrase("Tùy chọn phòng  ↓"); quiet: true; onClicked: root.detailsExpanded = !root.detailsExpanded }
            Button { visible: !hostBridge.details.active && plusFeaturesEnabled && multiplayerBridge.role === "hosting"; label: root.sharingExpanded ? Legacy.Tr.phrase("Thu gọn modpack") : Legacy.Tr.phrase("Đồng bộ modpack · Plus"); onClicked: root.sharingExpanded = !root.sharingExpanded }
        }
        Button { visible: multiplayerBridge.role === "joined" && root.detailsExpanded; objectName: "copyGuestRoomAddress"; label: Legacy.Tr.phrase("Chép địa chỉ vào Minecraft"); quiet: true; clickable: multiplayerBridge.localPort > 0; onClicked: multiplayerBridge.copyLocalAddress() }
        Flow {
            width: parent.width; spacing: 8
            visible: root.detailsExpanded && roomSyncBridge.hostReady
            Button { visible: multiplayerBridge.role === "hosting"; label: multiplayerBridge.locked ? Legacy.Tr.phrase("Mở khoá phòng") : Legacy.Tr.phrase("Khoá nhận khách mới"); quiet: true; onClicked: multiplayerBridge.setLocked(!multiplayerBridge.locked) }
        }
        Column {
            visible: root.stage === "waiting_world" && root.manualExpanded
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
