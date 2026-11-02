import QtQuick
import "../" as Legacy

// Một thẻ trong cửa sổ chọn khi bấm Chơi: thế giới (ảnh icon.png) hoặc server (icon servers.dat).
// Không có ảnh thì hiện key art của phiên bản — giống ô video không có thumbnail riêng.
Item {
    id: root
    property string imageUrl: ""
    property url fallbackUrl: ""
    property string title: ""
    property string subtitle: ""
    property var badges: []
    signal chosen
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: root.title + ", " + root.subtitle
    Accessible.onPressAction: root.chosen()
    Keys.onReturnPressed: root.chosen()
    Keys.onEnterPressed: root.chosen()
    Rectangle {
        id: card
        anchors.fill: parent
        radius: 16
        clip: true
        color: hover.hovered ? GlassTheme.raised : GlassTheme.cardSurface
        border.color: root.activeFocus || hover.hovered ? GlassTheme.alpha(GlassTheme.accent, 0.55) : GlassTheme.stroke
        Behavior on color { ColorAnimation { duration: GlassTheme.quick } }
        transform: Translate { y: hover.hovered && !GlassTheme.reducedMotion ? -3 : 0; Behavior on y { NumberAnimation { duration: GlassTheme.quick } } }
        Rectangle {
            id: thumbnail
            x: 1; y: 1
            width: parent.width - 2
            height: Math.round(width * 9 / 16)
            radius: card.radius - 1
            color: GlassTheme.selectedSurface
            clip: true
            Image {
                objectName: "playChoiceImage"
                anchors.fill: parent
                source: root.imageUrl || root.fallbackUrl
                // icon.png của game chỉ 64x64: phóng to giữ nét điểm ảnh như trong game.
                smooth: !root.imageUrl
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                opacity: root.imageUrl ? 1 : 0.55
                scale: hover.hovered && !GlassTheme.reducedMotion ? 1.04 : 1
                Behavior on scale { NumberAnimation { duration: GlassTheme.normal; easing.type: Easing.OutCubic } }
            }
            Row {
                anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 10
                spacing: 6
                Repeater {
                    model: root.badges
                    Rectangle {
                        height: 22; width: badgeText.implicitWidth + 16; radius: 11
                        color: modelData.danger ? GlassTheme.alpha(GlassTheme.danger, 0.85) : GlassTheme.alpha(GlassTheme.background, 0.78)
                        Text { id: badgeText; anchors.centerIn: parent; text: modelData.label; color: modelData.danger ? "white" : GlassTheme.text; font.family: GlassTheme.font; font.pixelSize: GlassTheme.fontCaption; font.weight: Font.DemiBold }
                    }
                }
            }
            Rectangle {
                anchors.centerIn: parent
                width: 52; height: 52; radius: 26
                visible: hover.hovered
                color: GlassTheme.alpha(GlassTheme.background, 0.72)
                border.color: GlassTheme.alpha(GlassTheme.accent, 0.7)
                Text { anchors.centerIn: parent; anchors.horizontalCenterOffset: 2; text: "▶"; color: GlassTheme.accent; font.pixelSize: 20 }
            }
        }
        Column {
            anchors.top: thumbnail.bottom; anchors.topMargin: 10
            x: 14; width: parent.width - 28
            spacing: 4
            Text { width: parent.width; text: root.title; color: GlassTheme.text; font.family: GlassTheme.font; font.pixelSize: GlassTheme.fontSubheading; font.weight: Font.DemiBold; elide: Text.ElideRight }
            Text { width: parent.width; text: root.subtitle; color: GlassTheme.muted; font.family: GlassTheme.font; font.pixelSize: GlassTheme.fontLabel; elide: Text.ElideRight }
        }
    }
    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: root.chosen() }
}
