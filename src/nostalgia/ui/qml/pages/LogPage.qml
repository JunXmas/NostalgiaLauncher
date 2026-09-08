import QtQuick
import "../"

/*
  NHẬT KÝ: output của game chảy vào đây theo thời gian thực, mỗi dòng tô màu theo cấp độ
  (INFO xám nhạt, WARN vàng, ERROR đỏ). Lọc theo cấp độ, tự cuộn theo dòng mới, sao chép
  toàn bộ để dán vào báo lỗi. Không có game nào chạy thì nói thẳng là chưa có gì.
*/
Item {
    id: page
    objectName: "logPage"
    property string minimumLevel: "info"   // info | warn | error
    property bool followTail: true
    readonly property var feed: bridge.gameLog

    function passes(level) {
        if (page.minimumLevel === "error") return level === "error";
        if (page.minimumLevel === "warn") return level !== "info";
        return true;
    }
    function colorFor(level) {
        return level === "error" ? Theme.danger : level === "warn" ? Theme.warning : Theme.textMuted;
    }

    Item {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right; margins: Theme.gap }
        height: 58
        Text {
            anchors { left: parent.left; top: parent.top }
            text: "Nhật ký"; color: Theme.text; font.pixelSize: 22; font.bold: true
        }
        Row {
            anchors { left: parent.left; top: parent.top; topMargin: 32 }
            spacing: 10
            StatusPill {
                dotColor: bridge.gameRunning ? Theme.accent : Theme.textMuted
                pulsing: bridge.gameRunning
                text: bridge.gameRunning ? "Game đang chạy" : "Game không chạy"
                height: 24
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: logList.count + " dòng"; color: Theme.textMuted; font.pixelSize: 12
            }
        }
        Row {
            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
            spacing: 8
            Repeater {
                model: [{ key: "info", text: "Tất cả" }, { key: "warn", text: "Cảnh báo+" }, { key: "error", text: "Lỗi" }]
                Rectangle {
                    width: chipText.width + 22; height: 30; radius: 15
                    color: page.minimumLevel === modelData.key ? Theme.accentSoft : Theme.surface
                    border.color: page.minimumLevel === modelData.key ? Theme.accent : Theme.border
                    Text { id: chipText; anchors.centerIn: parent; text: modelData.text; color: Theme.text; font.pixelSize: 12 }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.minimumLevel = modelData.key }
                }
            }
            ActionButton {
                objectName: "copyLogButton"
                primary: false; label: "⧉  Sao chép"
                clickable: logList.count > 0
                onClicked: page.feed.copyAll()
            }
        }
    }

    Panel {
        anchors { top: header.bottom; left: parent.left; right: parent.right; bottom: parent.bottom; margins: Theme.gap; topMargin: 6 }
        color: "#0b0f0c"

        ListView {
            id: logList
            objectName: "logList"
            anchors.fill: parent
            clip: true
            model: page.feed.logModel
            // Bám đuôi: dòng mới thì cuộn xuống, trừ khi người dùng đã kéo lên xem lại.
            onCountChanged: if (page.followTail) positionViewAtEnd()
            onMovingChanged: if (moving) page.followTail = atYEnd
            onAtYEndChanged: if (atYEnd) page.followTail = true
            delegate: Text {
                readonly property bool shown: page.passes(model.level)
                width: ListView.view.width
                height: shown ? implicitHeight + 3 : 0
                visible: shown
                text: model.text
                color: page.colorFor(model.level)
                font.family: "monospace"; font.pixelSize: 11
                wrapMode: Text.WrapAnywhere
                textFormat: Text.PlainText
            }
        }
        Text {
            visible: logList.count === 0
            anchors.centerIn: parent
            text: bridge.gameRunning ? "Đang chờ dòng đầu tiên..." : "Chưa có nhật ký. Bấm CHƠI, output của game sẽ hiện ở đây."
            color: Theme.textMuted; font.pixelSize: 12
        }
    }
}
