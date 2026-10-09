import QtQuick

Item {
    id: root
    property string label: ""
    property string icon: ""
    property string provider: ""
    property bool danger: false
    property bool primary: false
    property bool quiet: false
    property bool selected: false
    property bool emphasized: false
    property bool clickable: true
    readonly property bool hovered: hover.hovered
    readonly property real captionPadding: !root.provider && root.width <= 48 ? 4 : 16
    signal clicked
    implicitWidth: caption.implicitWidth + (root.provider ? providerLogo.width + labelRow.spacing : 0) + 32
    implicitHeight: 42
    width: implicitWidth
    height: implicitHeight
    scale: press.pressed && clickable ? 0.97 : 1
    Behavior on scale { NumberAnimation { duration: GlassTheme.quick; easing.type: Easing.OutCubic } }
    enabled: clickable
    activeFocusOnTab: true
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
        color: root.danger ? GlassTheme.alpha(GlassTheme.danger, hover.hovered ? 0.22 : 0.10) : root.primary ? (hover.hovered ? GlassTheme.primaryHover : GlassTheme.primaryFace) : root.selected ? GlassTheme.selectedSurface : root.quiet ? (hover.hovered ? GlassTheme.alpha(GlassTheme.accent, 0.10) : "transparent") : (hover.hovered ? GlassTheme.raised : GlassTheme.surface)
        border.color: root.activeFocus ? GlassTheme.accent : root.primary || root.quiet ? "transparent" : GlassTheme.stroke
        border.width: root.activeFocus ? 2 : 1
        opacity: root.clickable ? 1 : 0.4
        Behavior on color {
            ColorAnimation {
                duration: GlassTheme.quick
            }
        }
        Row {
            id: labelRow
            anchors.centerIn: parent; spacing: 10
            ProviderLogo { id: providerLogo; visible: !!root.provider; provider: root.provider; anchors.verticalCenter: parent.verticalCenter }
            Text {
                id: caption
                objectName: "buttonCaption"
                text: (root.icon ? root.icon + "  " : "") + root.label
                width: Math.max(0, Math.min(implicitWidth, root.width - root.captionPadding * 2 - (root.provider ? providerLogo.width + labelRow.spacing : 0)))
                elide: Text.ElideRight
                color: root.danger ? GlassTheme.danger : (root.selected || root.emphasized) && !root.primary ? GlassTheme.accent : GlassTheme.text
                font.family: GlassTheme.font; font.pixelSize: GlassTheme.fontControl; font.weight: Font.DemiBold
            }
        }
    }
    HoverHandler {
        id: hover
        cursorShape: root.clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
    TapHandler {
        id: press
        enabled: root.clickable
        onTapped: {
            root.forceActiveFocus();
            root.trigger();
        }
    }
}
