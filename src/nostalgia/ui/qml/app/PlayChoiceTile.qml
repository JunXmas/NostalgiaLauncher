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
            // Không có icon: key art phiên bản phủ kín khung.
            Image {
                anchors.fill: parent
                visible: !root.imageUrl
                source: root.imageUrl ? "" : root.fallbackUrl
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                opacity: 0.55
            }
            // Có icon (vuông 64x64): nền là chính icon giải mã 6x6 rồi phóng to — mờ sẵn mà không
            // cần shader, chạy cả trên GL phần mềm (cùng mẹo với CardMica).
            Image {
                anchors.fill: parent
                visible: !!root.imageUrl
                source: root.imageUrl
                sourceSize: Qt.size(6, 6)
                smooth: true
                fillMode: Image.PreserveAspectCrop
            }
            Rectangle { anchors.fill: parent; visible: !!root.imageUrl; color: GlassTheme.alpha(GlassTheme.background, 0.35) }
            Image {
                objectName: "playChoiceImage"
                anchors.centerIn: parent
                height: parent.height - 24; width: height
                visible: !!root.imageUrl
                source: root.imageUrl
                smooth: false  // icon game 64x64: giữ nét điểm ảnh như trong game
                fillMode: Image.PreserveAspectFit
                scale: hover.hovered && !GlassTheme.reducedMotion ? 1.05 : 1
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
                Text { anchors.centerIn: parent; anchors.horizontalCenterOffset: 2; text: "▶"; color: GlassTheme.accent; font.pixelSize: GlassTheme.fontSection }
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
