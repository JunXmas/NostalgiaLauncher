import QtQuick

/* Badge "● NOS CLIENT" + gear icon cho thẻ bản chơi.
   Badge click → toggle nos_client_enabled.
   Gear icon → popup cấu hình 6 HUD toggle. */
Item {
    id: root
    property bool nosEnabled: false
    property string instanceId: ""

    // Config HUD hiện tại (từ bridge).
    property bool nosCoords: true
    property bool nosDirection: true
    property bool nosDay: true
    property bool nosFps: false
    property bool nosPing: false
    property bool nosCps: false

    signal toggled(bool enabled)
    signal configChanged(bool coords, bool direction, bool day, bool fps, bool ping, bool cps)

    implicitWidth: badgeRow.width
    implicitHeight: 24

    Row {
        id: badgeRow
        spacing: 4
        anchors.verticalCenter: parent.verticalCenter

        // Badge chính: "● NOS CLIENT".
        Rectangle {
            width: badgeText.width + 16; height: 22; radius: 4
            color: root.nosEnabled ? "#1a4caf50" : "#1affffff"
            border.color: root.nosEnabled ? Theme.accent : Theme.border
            border.width: 1
            Behavior on color { ColorAnimation { duration: Theme.quick } }
            Behavior on border.color { ColorAnimation { duration: Theme.quick } }

            Text {
                id: badgeText
                anchors.centerIn: parent
                text: "● NOS CLIENT"
                font.pixelSize: 9; font.bold: true; font.letterSpacing: 0.5
                color: root.nosEnabled ? Theme.accent : Theme.textMuted
                Behavior on color { ColorAnimation { duration: Theme.quick } }
            }

            HoverHandler { id: badgeHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.toggled(!root.nosEnabled) }
        }

        // Gear icon: chỉ hiện khi enabled.
        Rectangle {
            visible: root.nosEnabled
            width: 22; height: 22; radius: 4
            color: gearHover.hovered ? Theme.surfaceHigh : "transparent"
            Behavior on color { ColorAnimation { duration: Theme.quick } }

            Text {
                anchors.centerIn: parent
                text: "⚙"; font.pixelSize: 11
                color: gearHover.hovered ? Theme.accent : Theme.textMuted
            }

            HoverHandler { id: gearHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: configPopup.visible = !configPopup.visible }
        }
    }

    // Popup cấu hình HUD: 6 checkbox.
    Rectangle {
        id: configPopup
        visible: false
        anchors { top: badgeRow.bottom; topMargin: 4 }
        width: 180; height: configCol.height + 24
        radius: Theme.radiusSmall
        color: "#e0111111"
        border.color: Theme.border; border.width: 1
        z: 100

        Column {
            id: configCol
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
            spacing: 6

            Text {
                text: "HUD Nos Client"
                color: Theme.text; font.pixelSize: 11; font.bold: true
            }

            Repeater {
                model: [
                    { label: "Coords (X/Y/Z)", key: "coords", checked: root.nosCoords },
                    { label: "Direction (La bàn)", key: "direction", checked: root.nosDirection },
                    { label: "Day (Ngày)", key: "day", checked: root.nosDay },
                    { label: "FPS", key: "fps", checked: root.nosFps },
                    { label: "Ping", key: "ping", checked: root.nosPing },
                    { label: "CPS (Click/s)", key: "cps", checked: root.nosCps }
                ]

                Item {
                    width: configCol.width; height: 20
                    required property var modelData
                    required property int index

                    Row {
                        spacing: 6
                        anchors.verticalCenter: parent.verticalCenter

                        Rectangle {
                            width: 14; height: 14; radius: 3
                            color: modelData.checked ? Theme.accent : "transparent"
                            border.color: modelData.checked ? Theme.accent : Theme.textMuted
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: modelData.checked ? "✓" : ""
                                color: "white"; font.pixelSize: 9
                            }
                        }

                        Text {
                            text: modelData.label
                            color: Theme.text; font.pixelSize: 11
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                    TapHandler {
                        onTapped: {
                            // Toggle và emit signal với toàn bộ state mới.
                            var c = root.nosCoords;
                            var d = root.nosDirection;
                            var dy = root.nosDay;
                            var f = root.nosFps;
                            var p = root.nosPing;
                            var cp = root.nosCps;
                            switch (modelData.key) {
                                case "coords": c = !c; break;
                                case "direction": d = !d; break;
                                case "day": dy = !dy; break;
                                case "fps": f = !f; break;
                                case "ping": p = !p; break;
                                case "cps": cp = !cp; break;
                            }
                            root.configChanged(c, d, dy, f, p, cp);
                        }
                    }
                }
            }
        }

        // Đóng popup khi click ra ngoài.
        MouseArea {
            id: closeArea
            parent: root.parent
            anchors.fill: parent
            visible: configPopup.visible
            z: 99
            onClicked: configPopup.visible = false
        }
    }
}
