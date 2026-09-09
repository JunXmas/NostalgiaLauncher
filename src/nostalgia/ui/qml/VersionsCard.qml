import QtQuick

/*
  Ô ở vị trí "NEWS" của bản mẫu.

  Bản mẫu để tin tức Modrinth/Mojang — lõi chưa lấy tin tức, và bịa ba dòng tin giả thì tệ
  hơn là bỏ trống. Chỗ này vì thế nói một sự thật hữu ích hơn: những phiên bản đã tải về máy,
  và một nút tải thêm.
*/
Panel {
    id: root
    property var versions: []
    property bool busy: false
    signal installRequested(string versionId)

    title: "PHIÊN BẢN ĐÃ TẢI"

    Column {
        anchors.fill: parent
        spacing: 9

        Text {
            visible: root.versions.length === 0
            width: parent.width
            text: "Chưa tải phiên bản nào."
            color: Theme.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.versions.slice(0, 4)
            Row {
                spacing: 9
                Rectangle {
                    width: 26; height: 26; radius: 6; color: Theme.accentSoft
                    anchors.verticalCenter: parent.verticalCenter
                    Text { anchors.centerIn: parent; text: "▣"; color: Theme.accent; font.pixelSize: 12 }
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData; color: Theme.text; font.pixelSize: 12
                }
            }
        }

        Row {
            width: parent.width
            spacing: 8
            TextField {
                id: wanted
                width: parent.width - installButton.width - 8
                placeholder: "vd. 1.20.1"
                onAccepted: root.installRequested(text)
            }
            ActionButton {
                id: installButton
                label: root.busy ? "Đang tải..." : "Tải"
                clickable: !root.busy
                onClicked: root.installRequested(wanted.text)
            }
        }
    }
}
