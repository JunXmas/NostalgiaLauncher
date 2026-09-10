import QtQuick

/*
  Ô CHƠI TIẾP ở cột phải trang chủ, hai nhóm: THẾ GIỚI chơi gần nhất trên mọi bản chơi, và
  SERVER đã thêm trong game (icon thật từ servers.dat). Mỗi dòng một nút khối; bấm là launcher mở
  đúng bản chơi và vào thẳng thế giới / máy chủ đó (quick play, 1.20+). Không ping server —
  trang chủ không chạm mạng.
*/
Panel {
    id: root
    property var worlds: []
    property var servers: []
    property bool playable: true
    signal worldChosen(string instanceId, string worldFolder)
    signal serverChosen(string instanceId, string address)

    title: "CHƠI TIẾP"

    Column {
        anchors.fill: parent
        spacing: 5
        Text { text: "THẾ GIỚI"; color: Theme.textMuted; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1.2 }
        Text {
            objectName: "continueEmpty"
            visible: root.worlds.length === 0
            width: parent.width; wrapMode: Text.WordWrap
            text: "Chưa có thế giới nào — vào game tạo một thế giới rồi quay lại đây."
            color: Theme.textMuted; font.pixelSize: 11; lineHeight: 1.25
        }
        Repeater {
            model: root.worlds.slice(0, 3)
            WorldButton {
                objectName: "continueRow"
                width: parent.width
                worldName: modelData.worldName
                detail: modelData.instanceLabel + "  ·  chơi " + modelData.lastPlayedText
                clickable: root.playable
                onChosen: root.worldChosen(modelData.instanceId, modelData.worldFolder)
            }
        }
        Text {
            topPadding: 6
            text: "SERVER"; color: Theme.textMuted; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1.2
        }
        Text {
            objectName: "continueServerEmpty"
            visible: root.servers.length === 0
            width: parent.width; wrapMode: Text.WordWrap
            text: "Chưa có server nào — thêm trong game (Multiplayer → Add Server) rồi quay lại đây."
            color: Theme.textMuted; font.pixelSize: 11; lineHeight: 1.25
        }
        Repeater {
            model: root.servers.slice(0, 3)
            WorldButton {
                objectName: "continueServerRow"
                width: parent.width
                worldName: modelData.serverName
                detail: modelData.address + "  ·  " + modelData.instanceLabel
                iconSource: modelData.iconUrl
                glyph: "◎"
                clickable: root.playable
                onChosen: root.serverChosen(modelData.instanceId, modelData.address)
            }
        }
    }
}
