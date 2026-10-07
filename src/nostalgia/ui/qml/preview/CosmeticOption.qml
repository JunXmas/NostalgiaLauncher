import QtQuick
import "CosmeticCatalog.js" as Cosmetics

Item {
    id: root
    property var cosmetic: ({})
    property bool selected: false
    property bool previewed: false
    property bool canEquip: false
    property string avatarSource: ""
    property string playerName: ""
    signal clicked
    implicitHeight: 172 * GlassTheme.scale
    height: implicitHeight
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: cosmetic.name + (selected ? ", đã chọn" : canEquip ? ", chọn trang trí hồ sơ" : ", xem thử, cần Pro để sử dụng")
    Accessible.onPressAction: root.clicked()
    Keys.onReturnPressed: root.clicked()
    Keys.onEnterPressed: root.clicked()
    Keys.onSpacePressed: function(event) { if (!event.isAutoRepeat) root.clicked(); }
    scale: tap.pressed ? 0.98 : 1
    Behavior on scale { NumberAnimation { duration: GlassTheme.quick; easing.type: Easing.OutCubic } }
    Rectangle {
        anchors.fill: parent; radius: 14
        color: hover.hovered ? GlassTheme.raised : GlassTheme.alpha(GlassTheme.surface, 0.7)
        border.width: root.activeFocus || root.selected ? 2 : 1
        border.color: root.activeFocus || root.selected ? root.cosmetic.tint : root.previewed ? GlassTheme.accent : GlassTheme.stroke
        Behavior on color { ColorAnimation { duration: GlassTheme.quick } }
    }
    Item {
        x: 5; y: 5; width: parent.width - 10; height: 95 * GlassTheme.scale; clip: true
        CosmeticBanner { anchors.fill: parent; radius: 10; decor: root.cosmetic.key; scrim: false }
        Rectangle { anchors.fill: parent; radius: 10; color: "#35100d1a" }
        SocialAvatar {
            anchors.centerIn: parent; size: 76 * GlassTheme.scale
            playerName: root.playerName; source: root.avatarSource; decor: root.cosmetic.key; showPresence: false
            scale: hover.hovered && !GlassTheme.reducedMotion ? 1.04 : 1
            Behavior on scale { NumberAnimation { duration: GlassTheme.normal; easing.type: Easing.OutCubic } }
        }
    }
    Column {
        x: 12; y: 109 * GlassTheme.scale; width: parent.width - 24; spacing: 5
        PaymentText { width: parent.width; text: root.cosmetic.name; font.weight: Font.DemiBold; font.pixelSize: GlassTheme.fontSubheading }
        PaymentText { width: parent.width; text: root.selected ? "✓ Đã chọn" : root.previewed ? "Đang xem thử" : root.canEquip ? root.cosmetic.description : "Xem thử · Pro"; color: root.selected ? root.cosmetic.tint : GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
    }
    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { id: tap; onTapped: { root.forceActiveFocus(); root.clicked(); } }
}
