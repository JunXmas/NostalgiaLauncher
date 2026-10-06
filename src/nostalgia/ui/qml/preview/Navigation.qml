import QtQuick
import "../" as Legacy

Glass {
    id: root
    property int currentIndex: 0
    signal navigate(int index)
    signal supportRequested
    padding: 16
    radius: 22
    readonly property var entries: [
        {
            label: "Trang chủ",
            block: "grass",
            index: 0
        },
        {
            label: "Bản chơi",
            block: "crafting",
            index: 1
        },
        {
            label: "Thư viện",
            block: "bookshelf",
            index: 2
        },
        {
            label: "Tài khoản",
            block: "diamond",
            index: 3
        },
        {
            label: "Bạn bè & chơi chung",
            block: "command",
            index: 4
        },
        {
            label: "Nhật ký",
            block: "barrel",
            index: 5
        }
    ]
    Row {
        id: brand
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 10
        spacing: 10
        Image {
            width: 30
            height: 30
            source: "../assets/logo.png"
            mipmap: true
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: "Nostalgia"
            color: GlassTheme.text
            font.family: GlassTheme.font
            font.pixelSize: GlassTheme.fontLead
            font.weight: Font.DemiBold
        }
    }
    InertialScroll {
        id: nav
        anchors.top: brand.bottom
        anchors.topMargin: 40
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: bottomLinks.top
        anchors.bottomMargin: 20
        contentHeight: links.height
        Column {
            id: links
            width: parent.width
            spacing: 6
            Text {
                x: 12
                height: 26
                text: "KHÔNG GIAN CỦA BẠN"
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: GlassTheme.fontMicro
                font.letterSpacing: 1.3
            }
            Repeater {
                model: root.entries
                Item {
                    id: navEntry
                    readonly property color tint: Legacy.Theme.accents[modelData.index]
                    width: links.width
                    height: 48 * GlassTheme.scale
                    activeFocusOnTab: true
                    Accessible.role: Accessible.Button
                    Accessible.name: modelData.label
                    function activate() {
                        root.navigate(modelData.index);
                    }
                    Accessible.onPressAction: activate()
                    Keys.onReturnPressed: activate()
                    Keys.onSpacePressed: function (event) {
                        if (!event.isAutoRepeat)
                            activate();
                    }
                    Rectangle {
                        anchors.fill: parent
                        radius: 12
                        color: root.currentIndex === modelData.index ? Legacy.Theme.mix(GlassTheme.raised, navEntry.tint, 0.22) : area.containsMouse ? GlassTheme.alpha(navEntry.tint, 0.08) : "transparent"
                        border.color: parent.activeFocus ? GlassTheme.accent : root.currentIndex === modelData.index ? GlassTheme.alpha(navEntry.tint, 0.25) : "transparent"
                        Behavior on color {
                            ColorAnimation {
                                duration: GlassTheme.quick
                            }
                        }
                    }
                    Legacy.BlockIcon {
                        x: 12
                        anchors.verticalCenter: parent.verticalCenter
                        width: 23
                        height: 23
                        block: modelData.block
                        glyph: "·"
                        spinning: false
                    }
                    Text {
                        x: 47
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.label
                        font.family: GlassTheme.font
                        font.pixelSize: GlassTheme.fontBody
                        font.weight: root.currentIndex === modelData.index ? Font.DemiBold : Font.Normal
                        color: root.currentIndex === modelData.index ? GlassTheme.text : GlassTheme.muted
                    }
                    MouseArea {
                        id: area
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: parent.activate()
                    }
                }
            }
        }
    }
    Column {
        id: bottomLinks
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: account.top
        anchors.bottomMargin: 18
        spacing: 2
        Button {
            width: parent.width
            label: "Cài đặt"
            quiet: true
            onClicked: root.navigate(6)
        }
        Item {
            width: parent.width
            height: 42
            Legacy.BlockIcon {
                x: 12
                anchors.verticalCenter: parent.verticalCenter
                width: 22
                height: 22
                block: "beacon"
                glyph: "·"
            }
            Button {
                anchors.left: parent.left
                anchors.leftMargin: 36
                width: parent.width - 36
                label: "Ủng hộ dự án"
                quiet: true
                objectName: "openSupport"
                onClicked: root.supportRequested()
            }
        }
        Button {
            width: parent.width
            label: "Cộng đồng  ↗"
            quiet: true
            onClicked: settingsBridge.openCommunityPage()
        }
    }
    Rectangle {
        id: account
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 68
        radius: 14
        color: GlassTheme.alpha(GlassTheme.surface, 0.70)
        border.color: GlassTheme.stroke
        Legacy.SkinFace {
            id: face
            x: 12
            anchors.verticalCenter: parent.verticalCenter
            size: 32
            readonly property var active: accountBridge.accounts.find(function (a) {
                return a.accountId === bridge.activeAccountId;
            }) || null
            source: active ? active.skinFile : ""
            visible: !!source && !socialBridge.signedIn
        }
        Rectangle {
            x: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 32
            height: 32
            radius: 10
            visible: !face.visible
            color: Legacy.Theme.mix(GlassTheme.surface, GlassTheme.brand, 0.20)
            Text {
                anchors.centerIn: parent
                text: socialBridge.signedIn ? socialBridge.account.name[0] : bridge.activePlayerName ? bridge.activePlayerName[0] : "?"
                color: GlassTheme.brand
                font.pixelSize: GlassTheme.fontHeading
            }
        }
        Column {
            x: 55
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - 64
            spacing: 4
            Text {
                width: parent.width
                text: socialBridge.signedIn ? socialBridge.account.name : bridge.activePlayerName || "Khách"
                color: GlassTheme.text
                font.family: GlassTheme.font
                font.pixelSize: GlassTheme.fontBody
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }
            Text {
                text: socialBridge.signedIn ? (socialBridge.account.plus ? "Google · Plus" : "Google · Miễn phí") : bridge.activePlayerName ? (face.active && face.active.accountKind === "microsoft" ? "Microsoft" : face.active && face.active.accountKind === "ely" ? "Ely.by" : "Ngoại tuyến") : "Chưa đăng nhập"
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: GlassTheme.fontNote
            }
        }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.navigate(socialBridge.signedIn ? 4 : 3)
        }
    }
}
