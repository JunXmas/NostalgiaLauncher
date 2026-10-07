import QtQuick
import QtQuick.Controls as Controls

Item {
    id: root
    objectName: "serverConsolePanel"
    property bool running: false
    Column { id: header; width: parent.width; spacing: 12
        Flow { width: parent.width; spacing: 10
            Button { objectName: "serverStart"; label: root.running ? "Dừng & lưu thế giới" : "Khởi chạy server"; primary: !root.running; clickable: !serverBridge.busy && (root.running || serverBridge.hasAccess && !serverBridge.runningId); onClicked: { if (root.running) serverBridge.stop(); else serverBridge.start(serverBridge.selected.server_id); } }
            Button { label: "Sao chép log"; quiet: true; onClicked: serverBridge.console.copyAll() }
            Button { objectName: "serverOpenFriends"; label: serverRoomBridge.active ? "Đóng kết nối bạn bè" : "Mở cho bạn bè"; clickable: !serverRoomBridge.busy && !serverBridge.busy && (serverRoomBridge.active || root.running && serverBridge.readyId === serverBridge.selected.server_id && !multiplayerBridge.active); onClicked: { if (serverRoomBridge.active) serverRoomBridge.close(); else serverRoomBridge.open(); } }
        }
        PaymentText { width: parent.width; text: serverRoomBridge.note; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
        PaymentText { width: parent.width; text: serverBridge.busy ? serverBridge.activity : "Kết nối trên máy này: localhost:" + ((serverBridge.selected.properties || {})["server-port"] || "25565") + ". Dùng địa chỉ máy host khi chơi trong mạng LAN."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
    }
    Rectangle {
        anchors.top: header.bottom; anchors.topMargin: 16; anchors.left: parent.left; anchors.right: parent.right
        anchors.bottom: inputRow.top; anchors.bottomMargin: 12
        color: GlassTheme.alpha(GlassTheme.surface, 0.6); radius: 14; border.color: GlassTheme.stroke
        ListView {
            id: log
            objectName: "serverLog"
            anchors.fill: parent; anchors.margins: 12
            clip: true; model: serverBridge.console.logModel
            delegate: PaymentText { width: log.width - 12; text: model.text; color: model.level === "error" ? "#ef8c9a" : model.level === "warn" ? "#e9c482" : GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption; wrapMode: Text.WrapAnywhere }
            onCountChanged: if (atYEnd || count < 20) positionViewAtEnd()
            Controls.ScrollBar.vertical: Controls.ScrollBar { }
        }
    }
    Row { id: inputRow; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; spacing: 10
        Input { id: command; objectName: "serverCommand"; width: Math.max(140, parent.width - send.width - 10); placeholder: "say Xin chào / whitelist add Player / save-all…"; enabled: root.running; onAccepted: send.trigger() }
        Button { id: send; objectName: "serverCommandSend"; label: "Gửi lệnh"; clickable: root.running && !serverBridge.busy && !!command.text.trim(); onClicked: { serverBridge.command(command.text); command.text = ""; } }
    }
}
