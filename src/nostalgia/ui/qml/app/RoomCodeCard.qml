import QtQuick
import "../" as Legacy

/* Mã phòng ngay trên trang Bạn bè: chủ phòng thấy mã + Chép, khách nhập mã + Vào.
   Vào bằng mã đi đúng đường của lời mời (`roomSyncBridge.join`), không có đường mạng riêng. */
Glass {
    id: root
    objectName: "roomCodeCard"
    readonly property bool hosting: (multiplayerBridge.role === "hosting" || multiplayerBridge.role === "waiting_world") && !!multiplayerBridge.roomCode
    readonly property bool joined: multiplayerBridge.role === "joined"
    readonly property bool preparing: !root.hosting && !root.joined && (multiplayerBridge.active || hostBridge.details.active)
    readonly property bool canJoin: codeInput.complete && !multiplayerBridge.active && !hostBridge.details.active && roomSyncBridge.hostReady && !roomSyncBridge.busy
    property bool showRoomButton: true
    signal openRoom()
    function join() { if (root.canJoin) roomSyncBridge.join(codeInput.code); }
    padding: 18
    implicitHeight: contents.implicitHeight + 36
    height: implicitHeight
    Column {
        id: contents
        width: parent.width; spacing: 12
        PaymentText {
            width: parent.width
            text: root.hosting ? Legacy.Tr.phrase("Mã phòng của bạn") : root.joined ? Legacy.Tr.phrase("Bạn đang ở phòng của bạn bè") : root.preparing ? Legacy.Tr.phrase("Đang tạo phòng") : Legacy.Tr.phrase("Có mã phòng?")
            font.pixelSize: GlassTheme.fontHeading; font.weight: Font.DemiBold
        }
        PaymentText {
            width: parent.width
            text: root.hosting ? Legacy.Tr.phrase("Gửi mã này cho bạn bè, hoặc bấm Mời cạnh tên họ.")
                : root.joined ? Legacy.Tr.phrase("Xem phòng để đồng bộ modpack và vào world.")
                : root.preparing ? Legacy.Tr.phrase("Mã phòng hiện ở đây khi phòng sẵn sàng.")
                : Legacy.Tr.phrase("Nhập mã 18 ký tự bạn bè gửi rồi bấm Vào.")
            color: GlassTheme.muted
        }
        Text {
            objectName: "hostRoomCode"
            visible: root.hosting
            text: multiplayerBridge.roomCodeSpaced
            color: GlassTheme.text; font.family: "monospace"; font.bold: true; font.pixelSize: GlassTheme.fontTitle
        }
        Legacy.RoomCodeInput {
            id: codeInput
            objectName: "roomCodeInput"
            visible: !root.hosting && !root.joined && !root.preparing
            onSubmitted: root.join()
        }
        Flow {
            width: parent.width; spacing: 8
            Button { objectName: "copyRoomCode"; visible: root.hosting; label: Legacy.Tr.phrase("Chép mã"); primary: true; onClicked: multiplayerBridge.copyRoomCode() }
            Button { objectName: "joinRoomCode"; visible: codeInput.visible; label: Legacy.Tr.phrase("Vào"); primary: true; clickable: root.canJoin; onClicked: root.join() }
            Button { objectName: "pasteRoomCode"; visible: codeInput.visible; label: Legacy.Tr.phrase("Dán"); quiet: true; onClicked: codeInput.setCode(multiplayerBridge.clipboardText()) }
            Button { objectName: "showActiveRoom"; visible: root.showRoomButton && !codeInput.visible; label: root.hosting && roomSyncBridge.hostReady ? Legacy.Tr.phrase("Xem phòng chơi · Mời bạn bè") : Legacy.Tr.phrase("Xem phòng chơi"); quiet: root.hosting; onClicked: root.openRoom() }
        }
    }
}
