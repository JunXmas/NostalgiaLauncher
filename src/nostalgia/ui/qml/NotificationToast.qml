import QtQuick

/*
  Toast sự kiện (game khởi động / thoát / sự cố / cài xong): góc dưới phải, trượt lên, tự ẩn
  sau vài giây, bấm để tắt ngay. Nhiều sự kiện dồn dập thì xếp hàng, hiện lần lượt. Âm thanh
  do `Notifier` ở Python phát — QML chỉ vẽ.
*/
Item {
    id: root
    // Cao thêm khi popup loading đang chiếm góc, để hai cái không đè nhau.
    property int bottomOffset: Theme.gap
    property var pending: []
    property var current: null

    anchors.fill: parent

    function showNext() {
        if (root.pending.length === 0) { root.current = null; return; }
        root.current = root.pending.shift();
        root.pending = root.pending;
        hideLater.restart();
    }

    Connections {
        target: notifier
        function onNotified(eventKind, title, detail) {
            root.pending.push({ eventKind: eventKind, title: title, detail: detail });
            root.pending = root.pending;
            if (root.current === null) root.showNext();
        }
    }
    Timer { id: hideLater; interval: 4200; onTriggered: root.showNext() }

    Rectangle {
        id: card
        objectName: "notificationToast"
        readonly property bool shown: root.current !== null
        readonly property string eventKind: shown ? root.current.eventKind : ""
        readonly property color accentColor: eventKind === "crashed" ? Theme.danger : Theme.accent
        width: 320; height: 64
        radius: Theme.radiusSmall
        color: "#f2111713"
        border.color: card.accentColor
        border.width: 1
        anchors { right: parent.right; bottom: parent.bottom; margins: Theme.gap }
        anchors.bottomMargin: shown ? root.bottomOffset : -height - 10
        opacity: shown ? 1 : 0
        Behavior on anchors.bottomMargin { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        Behavior on opacity { NumberAnimation { duration: Theme.normal } }

        Rectangle {
            id: glyphBox
            width: 36; height: 36; radius: 8
            anchors { left: parent.left; leftMargin: 14; verticalCenter: parent.verticalCenter }
            color: card.eventKind === "crashed" ? "#3a1c1e" : Theme.accentSoft
            Text {
                anchors.centerIn: parent
                text: card.eventKind === "started" ? "▶" : card.eventKind === "crashed" ? "✕"
                      : card.eventKind === "installed" ? "✓" : card.eventKind === "update" ? "⬆" : "■"
                color: card.accentColor; font.pixelSize: 15; font.bold: true
            }
        }
        Column {
            anchors { left: glyphBox.right; leftMargin: 12; right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
            spacing: 3
            Text {
                objectName: "notificationTitle"
                width: parent.width
                text: card.shown ? root.current.title : ""
                color: Theme.text; font.pixelSize: 12; font.bold: true; elide: Text.ElideRight
            }
            Text {
                width: parent.width
                text: card.shown ? root.current.detail : ""
                color: Theme.textMuted; font.pixelSize: 11; elide: Text.ElideRight
            }
        }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.showNext() }
    }
}
