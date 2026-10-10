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
            label: Legacy.Tr.phrase("Trang chủ"),
            block: "grass",
            index: 0
        },
        {
            label: Legacy.Tr.phrase("Bản chơi"),
            block: "crafting",
            index: 1
        },
        {
            label: Legacy.Tr.phrase("Thư viện"),
            block: "bookshelf",
            index: 2
        },
        { label: Legacy.Tr.phrase("Cosmetic"), block: "amethyst", index: 7 },
        {
            label: Legacy.Tr.phrase("Tài khoản"),
            block: "diamond",
            index: 3
        },
        {
            label: Legacy.Tr.phrase("Bạn bè"),
            block: "command",
            index: 4
        },
        {
            label: Legacy.Tr.phrase("Nhật ký"),
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
        Rectangle {
            readonly property int selectedPosition: root.entries.findIndex(function(e) { return e.index === root.currentIndex; })
            readonly property color tint: Legacy.Theme.accents[root.currentIndex === 7 ? 3 : Math.min(5, root.currentIndex)]
            objectName: "navigationIndicator"
            width: links.width; height: 48 * GlassTheme.scale
            y: 32 + Math.max(0, selectedPosition) * (48 * GlassTheme.scale + 6)
            radius: 12
            opacity: selectedPosition >= 0 ? 1 : 0
            color: Legacy.Theme.mix(GlassTheme.raised, tint, 0.22)
            Behavior on y { NumberAnimation { duration: GlassTheme.normal; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: GlassTheme.normal } }
            Behavior on opacity { NumberAnimation { duration: GlassTheme.quick } }
        }
        Column {
            id: links
            width: parent.width
            spacing: 6
            Text {
                x: 12
                height: 26
                text: Legacy.Tr.phrase("KHÔNG GIAN CỦA BẠN")
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: GlassTheme.fontMicro
                font.letterSpacing: 1.3
            }
            Repeater {
                model: root.entries
                Item {
                    id: navEntry
                    objectName: "navigationEntry-" + modelData.index
                    readonly property color tint: Legacy.Theme.accents[modelData.index === 7 ? 3 : modelData.index]
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
                        color: area.containsMouse ? GlassTheme.alpha(navEntry.tint, 0.08) : "transparent"
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
                        objectName: "navigationBlock-" + modelData.index
                        spinning: area.containsMouse || navEntry.activeFocus
                    }
                    Text {
                        x: 47
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - x - 10
                        elide: Text.ElideRight
                        text: modelData.label
                        font.family: GlassTheme.font
                        font.pixelSize: GlassTheme.fontBody
                        font.weight: root.currentIndex === modelData.index ? Font.DemiBold : Font.Normal
                        color: root.currentIndex === modelData.index ? GlassTheme.text : GlassTheme.muted
                    }
                    MouseArea {
                        id: area
                        objectName: "navigationHit-" + modelData.index
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
        Item {
            width: parent.width; height: 42
            Legacy.BlockIcon {
                x: 12; anchors.verticalCenter: parent.verticalCenter
                width: 22; height: 22; block: "redstone"; glyph: "·"
                spinning: settingsAction.hovered
            }
            Button {
                id: settingsAction
                anchors.left: parent.left; anchors.leftMargin: 36
                width: parent.width - 36; label: Legacy.Tr.phrase("Cài đặt"); quiet: true
                onClicked: root.navigate(6)
            }
        }
        Item {
            width: parent.width
            height: Math.max(60, premiumLabels.implicitHeight + 16)
            Legacy.BlockIcon {
                x: 12
                anchors.verticalCenter: parent.verticalCenter
                width: 22
                height: 22
                block: "beacon"
                id: supportBeacon
                objectName: "supportBlock"
                spinning: supportHover.hovered || donateHover.hovered
                HoverHandler { id: supportHover }
                glyph: "·"
            }
            Button {
                anchors.left: parent.left
                anchors.leftMargin: 36
                width: parent.width - 36
                height: parent.height
                Accessible.name: Legacy.Tr.phrase("Premium · Mua gói và nâng cấp")
                quiet: true
                objectName: "openSupport"
                HoverHandler { id: donateHover }
                onClicked: root.supportRequested()
                Column {
                    id: premiumLabels
                    objectName: "premiumNavigationLabels"
                    anchors.centerIn: parent
                    width: parent.width - 24
                    spacing: 4
                    PaymentText {
                        width: parent.width; text: "Premium"
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: GlassTheme.fontControl; font.weight: Font.DemiBold
                        maximumLineCount: 1; elide: Text.ElideRight
                    }
                    PaymentText {
                        width: parent.width; text: Legacy.Tr.phrase("Mua gói & nâng cấp")
                        horizontalAlignment: Text.AlignHCenter
                        color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption
                        maximumLineCount: 1; elide: Text.ElideRight
                    }
                }
            }
        }
        Button {
            width: parent.width
            label: Legacy.Tr.phrase("Cộng đồng  ↗")
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
            visible: !face.visible && !socialBridge.signedIn
            color: Legacy.Theme.mix(GlassTheme.surface, GlassTheme.brand, 0.20)
            Text {
                anchors.centerIn: parent
                text: socialBridge.signedIn ? socialBridge.account.name[0] : bridge.activePlayerName ? bridge.activePlayerName[0] : "?"
                color: GlassTheme.brand
                font.pixelSize: GlassTheme.fontHeading
            }
        }
        SocialAvatar { objectName: "ownProfileAvatar"; decor: cosmeticBridge.details.decor || "none"; x: 12; anchors.verticalCenter: parent.verticalCenter; size: 32; visible: socialBridge.signedIn; playerName: socialBridge.account.name || ""; source: socialBridge.account.avatarUrl || ""; showPresence: false; clickable: true; onClicked: socialProfileDialog.showFor(socialBridge.account.accountId) }
        Button { objectName: "socialAccountToggle"; anchors.right: parent.right; anchors.rightMargin: 6; anchors.verticalCenter: parent.verticalCenter; width: 36; height: 36; chevron: true; Accessible.name: Legacy.Tr.phrase("Menu tài khoản Google và Minecraft"); onClicked: accountMenu.open() }
        Column {
            x: 55
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - 105
            spacing: 4
            Text {
                width: parent.width
                text: socialBridge.signedIn ? socialBridge.account.name : bridge.activePlayerName || Legacy.Tr.phrase("Khách")
                color: GlassTheme.text
                font.family: GlassTheme.font
                font.pixelSize: GlassTheme.fontBody
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                text: typeof draftReviewController !== "undefined" && draftReviewController !== null && socialBridge.signedIn ? "Local TEST · " + socialBridge.account.planName : socialBridge.signedIn ? (socialBridge.account.plus ? "Google · " + socialBridge.account.planName : Legacy.Tr.phrase("Google · Miễn phí")) : bridge.activePlayerName ? (face.active && face.active.accountKind === "microsoft" ? "Microsoft" : face.active && face.active.accountKind === "ely" ? "Ely.by" : Legacy.Tr.phrase("Ngoại tuyến")) : Legacy.Tr.phrase("Chưa đăng nhập")
                elide: Text.ElideRight
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: GlassTheme.fontNote
            }
        }
        MouseArea {
            x: 55; width: parent.width - 105; height: parent.height
            cursorShape: Qt.PointingHandCursor
            onClicked: { if (socialBridge.signedIn) socialProfileDialog.showFor(socialBridge.account.accountId); else root.navigate(3); }
        }
    }
    AccountMenu { id: accountMenu; anchorItem: account; onNavigate: function(index) { root.navigate(index); } }
}
