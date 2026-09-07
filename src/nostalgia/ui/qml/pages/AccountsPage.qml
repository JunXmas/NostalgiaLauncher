import QtQuick
import "../"

/*
  TÀI KHOẢN, bố cục theo bản mẫu: trái là danh sách (avatar cắt từ skin, tên, nhãn loại, ✓ tài
  khoản đang dùng, ✕ gỡ) và tab Skin/Cape; phải là cột xem nhân vật vẽ từ skin, mũi tên ‹ › xoay
  bốn hướng. Ba cách thêm: Microsoft (premium), Ely.by (non-premium có skin), ngoại tuyến.
*/
Item {
    id: page
    objectName: "accountsPage"
    signal navigate(int pageIndex)
    property string shownName: bridge.activePlayerName
    property int facing: 0
    property string tab: "skin"
    readonly property var shown: accountBridge.accountNamed(page.shownName)
    readonly property bool hasShown: shown && shown.playerName !== undefined

    Connections {
        target: bridge
        function onActiveAccountChanged() { page.shownName = bridge.activePlayerName; }
    }

    Item {
        id: header
        anchors { top: parent.top; left: parent.left; right: rightColumn.left; margins: Theme.gap }
        height: 58
        Text {
            anchors { left: parent.left; top: parent.top }
            text: "Tài khoản"; color: Theme.text; font.pixelSize: 22; font.bold: true
        }
        Text {
            anchors { left: parent.left; top: parent.top; topMargin: 32 }
            text: "Quản lý tài khoản Minecraft: premium (Microsoft) và non-premium (Ely.by)."
            color: Theme.textMuted; font.pixelSize: 12
        }
        ActionButton {
            objectName: "addAccountButton"
            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
            label: "+  Thêm tài khoản"
            onClicked: addDialog.openDialog()
        }
    }

    // ----- danh sách -----
    Panel {
        id: listPanel
        anchors { top: header.bottom; left: parent.left; right: rightColumn.left; margins: Theme.gap; topMargin: 6 }
        height: Math.min(parent.height * 0.52, 90 + accountBridge.accounts.length * 62)
        title: accountBridge.accounts.length + " TÀI KHOẢN"

        ListView {
            anchors.fill: parent
            clip: true; spacing: 8
            model: accountBridge.accounts
            delegate: Rectangle {
                id: row
                readonly property bool active: modelData.playerName === bridge.activePlayerName
                readonly property bool shownHere: modelData.playerName === page.shownName
                width: ListView.view.width; height: 54; radius: Theme.radiusSmall
                color: active ? Theme.accentSoft : (rowHover.containsMouse ? Theme.surfaceHigh : "transparent")
                border.color: active ? Theme.accent : (shownHere ? Theme.border : "transparent")
                Row {
                    anchors { left: parent.left; leftMargin: 10; verticalCenter: parent.verticalCenter }
                    spacing: 12
                    SkinFace { size: 36; source: modelData.skinFile; anchors.verticalCenter: parent.verticalCenter }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter; spacing: 3
                        Row {
                            spacing: 8
                            Text { text: modelData.playerName; color: Theme.text; font.pixelSize: 13; font.bold: true }
                            Rectangle {
                                anchors.verticalCenter: parent.verticalCenter
                                width: kindText.width + 12; height: 16; radius: 4
                                color: modelData.accountKind === "microsoft" ? "#1d4d13" : Theme.surfaceHigh
                                border.color: Theme.border
                                Text { id: kindText; anchors.centerIn: parent; text: modelData.kindLabel
                                       color: Theme.text; font.pixelSize: 9; font.bold: true; font.letterSpacing: 0.8 }
                            }
                        }
                        Text { text: modelData.playerUuid.slice(0, 8) + "···"; color: Theme.textMuted; font.pixelSize: 10; font.family: "monospace" }
                    }
                }
                Text {
                    anchors { right: parent.right; rightMargin: 40; verticalCenter: parent.verticalCenter }
                    visible: row.active; text: "✓"; color: Theme.accent; font.pixelSize: 16; font.bold: true
                }
                Text {
                    anchors { right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
                    text: "✕"; font.pixelSize: 12
                    color: removeArea.containsMouse ? Theme.danger : Theme.textMuted
                    opacity: rowHover.containsMouse ? 1 : 0
                    MouseArea { id: removeArea; anchors.fill: parent; anchors.margins: -6; hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor; onClicked: bridge.removeAccount(modelData.playerName) }
                }
                MouseArea {
                    id: rowHover
                    anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    z: -1
                    onClicked: { page.shownName = modelData.playerName; bridge.setActiveAccount(modelData.playerName); }
                }
            }
        }
        Text {
            visible: accountBridge.accounts.length === 0
            text: "Chưa có tài khoản — bấm Thêm tài khoản."; color: Theme.textMuted; font.pixelSize: 12
        }
    }

    // ----- skin / cape -----
    SkinPanel {
        anchors { top: listPanel.bottom; left: parent.left; right: rightColumn.left; bottom: parent.bottom; margins: Theme.gap; topMargin: 10 }
        shown: page.shown; hasShown: page.hasShown; tab: page.tab
    }

    // ----- cột phải: nhân vật -----
    Rectangle {
        id: rightColumn
        anchors { top: parent.top; right: parent.right; bottom: parent.bottom }
        width: 300
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0d1a11" }
            GradientStop { position: 1.0; color: "#08110b" }
        }
        Rectangle {
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
            width: 1; color: Theme.border
        }

        SkinFigure {
            id: figure
            anchors { horizontalCenter: parent.horizontalCenter; top: parent.top; topMargin: 110 }
            pixel: 8
            source: page.hasShown ? page.shown.skinFile : ""
            slim: page.hasShown ? page.shown.slim : false
            facing: page.facing
            visible: page.hasShown
        }
        Text {
            anchors { left: parent.left; leftMargin: 14; verticalCenter: figure.verticalCenter }
            text: "‹"; color: Theme.text; font.pixelSize: 30
            MouseArea { anchors.fill: parent; anchors.margins: -10; cursorShape: Qt.PointingHandCursor; onClicked: page.facing = (page.facing + 3) % 4 }
        }
        Text {
            anchors { right: parent.right; rightMargin: 14; verticalCenter: figure.verticalCenter }
            text: "›"; color: Theme.text; font.pixelSize: 30
            MouseArea { anchors.fill: parent; anchors.margins: -10; cursorShape: Qt.PointingHandCursor; onClicked: page.facing = (page.facing + 1) % 4 }
        }
        Column {
            anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 26 }
            spacing: 6
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: page.hasShown ? page.shown.playerName : "Chưa chọn"
                   color: Theme.text; font.pixelSize: 16; font.bold: true }
            Text { anchors.horizontalCenter: parent.horizontalCenter; visible: page.hasShown
                   text: page.hasShown ? page.shown.playerUuid : ""; color: Theme.textMuted; font.pixelSize: 9; font.family: "monospace" }
            Text { anchors.horizontalCenter: parent.horizontalCenter; visible: page.hasShown
                   text: page.hasShown ? page.shown.kindLabel + (page.shown.slim ? "  ·  Slim" : "  ·  Wide") : ""; color: Theme.accent; font.pixelSize: 10; font.letterSpacing: 1 }
        }
    }

    AddAccountDialog { id: addDialog; objectName: "addAccountDialog"; anchors.fill: parent }
}
