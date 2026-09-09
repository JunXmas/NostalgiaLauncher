import QtQuick

/*
  Ô CHƠI TIẾP ở cột phải trang chủ: các thế giới chơi gần nhất trên mọi bản chơi, mỗi thế giới
  một nút khối; bấm là launcher mở đúng bản chơi và vào thẳng thế giới đó (quick play, 1.20+).
  Thay cho ô "Phiên bản đã tải" trước đây — kho phiên bản là chuyện của launcher, không phải
  của người chơi.
*/
Panel {
    id: root
    property var worlds: []
    property bool playable: true
    signal worldChosen(string instanceId, string worldFolder)

    title: "CHƠI TIẾP"

    Column {
        anchors.fill: parent
        spacing: 5
        Text {
            objectName: "continueEmpty"
            visible: root.worlds.length === 0
            width: parent.width; wrapMode: Text.WordWrap
            text: "Chưa có thế giới nào. Vào game tạo một thế giới rồi quay lại đây — bấm một cái là vào thẳng."
            color: Theme.textMuted; font.pixelSize: 11; lineHeight: 1.25
        }
        Repeater {
            model: root.worlds.slice(0, 4)
            WorldButton {
                objectName: "continueRow"
                width: parent.width
                worldName: modelData.worldName
                detail: modelData.instanceLabel + "  ·  chơi " + modelData.lastPlayedText
                clickable: root.playable
                onChosen: root.worldChosen(modelData.instanceId, modelData.worldFolder)
            }
        }
    }
}
