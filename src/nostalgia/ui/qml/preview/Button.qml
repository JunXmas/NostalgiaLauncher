import QtQuick

Item {
    id: root
    property string label: ""
    property string icon: ""
    property bool primary: false
    property bool quiet: false
    property bool selected: false
    property bool clickable: true
    signal clicked
    implicitWidth: caption.implicitWidth + 32
    implicitHeight: 42
    width: implicitWidth
    height: implicitHeight
    activeFocusOnTab: clickable
    Accessible.role: Accessible.Button
    Accessible.name: label
    Accessible.onPressAction: root.trigger()
    Keys.onReturnPressed: root.trigger()
    Keys.onEnterPressed: root.trigger()
    Keys.onSpacePressed: function (event) {
        if (!event.isAutoRepeat)
            root.trigger();
    }
    function trigger() {
        if (clickable)
            root.clicked();
    }
    Rectangle {
        anchors.fill: parent
        radius: 12
        color: root.primary ? (hover.hovered ? GlassTheme.primaryHover : GlassTheme.primaryFace) : root.selected ? GlassTheme.selectedSurface : root.quiet ? (hover.hovered ? GlassTheme.alpha(GlassTheme.accent, 0.10) : "transparent") : (hover.hovered ? GlassTheme.raised : GlassTheme.surface)
        border.color: root.activeFocus ? GlassTheme.accent : root.primary || root.quiet ? "transparent" : GlassTheme.stroke
        border.width: root.activeFocus ? 2 : 1
        opacity: root.clickable ? 1 : 0.4
        Behavior on color {
            ColorAnimation {
                duration: GlassTheme.quick
            }
        }
        Text {
            id: caption
            anchors.centerIn: parent
            text: (root.icon ? root.icon + "  " : "") + root.label
            color: root.selected && !root.primary ? GlassTheme.accent : GlassTheme.text
            font.family: GlassTheme.font
            font.pixelSize: 14 * GlassTheme.scale
            font.weight: Font.DemiBold
        }
    }
    HoverHandler {
        id: hover
        cursorShape: root.clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
    TapHandler {
        enabled: root.clickable
        onTapped: {
            root.forceActiveFocus();
            root.trigger();
        }
    }
}
