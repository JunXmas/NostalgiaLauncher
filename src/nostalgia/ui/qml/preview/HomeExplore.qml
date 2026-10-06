import QtQuick
import "../" as Legacy

Grid {
    id: root
    signal navigate(int index)
    columns: width >= 700 * GlassTheme.scale ? 2 : 1
    spacing: 16
    Repeater {
        model: [
            {
                title: "Một thế giới khác để khám phá",
                description: "Modpack, shader và tài nguyên cho lần chơi tiếp theo.",
                block: "bookshelf",
                page: 2
            },
            {
                title: "Có bạn, vui hơn một chút",
                description: "Mở Chơi chung và tiếp tục hành trình cùng bạn bè.",
                block: "command",
                page: 4
            }
        ]
        Glass {
            width: (root.width - (root.columns - 1) * root.spacing) / root.columns
            height: Math.max(112, labels.implicitHeight + 40)
            padding: 20
            radius: 18
            color: GlassTheme.alpha(GlassTheme.surface, 0.75)
            activeFocusOnTab: true
            Accessible.role: Accessible.Button
            Accessible.name: modelData.title
            Accessible.onPressAction: root.navigate(modelData.page)
            Keys.onReturnPressed: root.navigate(modelData.page)
            Keys.onSpacePressed: function (event) {
                if (!event.isAutoRepeat)
                    root.navigate(modelData.page);
            }
            border.color: activeFocus || hover.hovered ? GlassTheme.accent : GlassTheme.stroke
            Legacy.BlockIcon {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: 40
                height: 40
                block: modelData.block
            }
            Column {
                id: labels
                x: 58
                width: parent.width - 78
                anchors.verticalCenter: parent.verticalCenter
                spacing: 7
                PaymentText {
                    width: parent.width
                    text: modelData.title
                    font.weight: Font.DemiBold
                }
                PaymentText {
                    width: parent.width
                    text: modelData.description
                    color: GlassTheme.muted
                    font.pixelSize: GlassTheme.fontNote
                }
            }
            PaymentText {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: "↗"
                color: GlassTheme.muted
            }
            HoverHandler {
                id: hover
                cursorShape: Qt.PointingHandCursor
            }
            TapHandler {
                onTapped: root.navigate(modelData.page)
            }
        }
    }
}
