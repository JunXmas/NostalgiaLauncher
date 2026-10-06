import QtQuick

Rectangle {
    id: root
    property string style: ""
    property string title: ""
    property string description: ""
    property url previewSource
    property bool selected: false
    property bool compact: false
    signal chosen(string style)
    implicitHeight: contents.implicitHeight + 32
    height: implicitHeight
    radius: 18
    color: GlassTheme.alpha(GlassTheme.surface, 0.88)
    border.color: selected || activeFocus ? GlassTheme.accent : GlassTheme.stroke
    border.width: selected || activeFocus ? 2 : 1
    activeFocusOnTab: true
    Accessible.role: Accessible.RadioButton
    Accessible.name: title + ". " + description
    Accessible.checkable: true
    Accessible.checked: selected
    Accessible.onPressAction: root.chosen(root.style)
    Keys.onReturnPressed: root.chosen(root.style)
    Keys.onEnterPressed: root.chosen(root.style)
    Keys.onSpacePressed: function (event) {
        if (!event.isAutoRepeat)
            root.chosen(root.style);
    }
    Column {
        id: contents
        x: 16
        y: 16
        width: parent.width - 32
        spacing: root.compact ? 12 : 16
        Rectangle {
            width: parent.width
            height: width * (root.compact ? 0.30 : 0.625)
            radius: 10
            color: GlassTheme.background
            Image {
                objectName: "interfaceImage-" + root.style
                anchors.fill: parent
                anchors.margins: 2
                source: root.previewSource
                fillMode: Image.PreserveAspectFit
                mipmap: true
            }
        }
        Row {
            width: parent.width
            spacing: 12
            Column {
                width: parent.width - 40
                spacing: 7
                PaymentText {
                    width: parent.width
                    text: root.title
                    font.pixelSize: (root.compact ? 17 : 19) * GlassTheme.scale
                    font.weight: Font.DemiBold
                }
                PaymentText {
                    width: parent.width
                    text: root.description
                    color: GlassTheme.muted
                    font.pixelSize: GlassTheme.fontLabel
                }
            }
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 26
                height: 26
                radius: 13
                color: root.selected ? GlassTheme.accent : "transparent"
                border.color: root.selected ? GlassTheme.accent : GlassTheme.muted
                PaymentText {
                    anchors.centerIn: parent
                    text: root.selected ? "✓" : ""
                    font.pixelSize: GlassTheme.fontAction
                    color: GlassTheme.background
                }
            }
        }
    }
    HoverHandler {
        id: hover
        cursorShape: Qt.PointingHandCursor
    }
    TapHandler {
        onTapped: {
            root.forceActiveFocus();
            root.chosen(root.style);
        }
    }
}
