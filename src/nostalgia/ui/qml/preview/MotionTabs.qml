import QtQuick
Item {
    id: root
    property var labels: []
    property int currentIndex: 0
    property string namePrefix: "tab-"
    signal selected(int index)
    function refreshSelection() { selection.selectedButton = choices.itemAt(root.currentIndex); }
    onCurrentIndexChanged: Qt.callLater(refreshSelection)
    implicitWidth: tabs.implicitWidth + 8
    implicitHeight: tabs.implicitHeight + 8
    height: implicitHeight
    Rectangle { anchors.fill: parent; radius: 15; color: GlassTheme.alpha(GlassTheme.raised, 0.40); border.color: GlassTheme.stroke }
    Rectangle {
        id: selection
        property Item selectedButton: null
        x: selectedButton ? selectedButton.x + 4 : 4; y: selectedButton ? selectedButton.y + 4 : 4
        width: selectedButton ? selectedButton.width : 0; height: selectedButton ? selectedButton.height : 0
        radius: 11; color: GlassTheme.selectedSurface; border.color: GlassTheme.alpha(GlassTheme.accent, 0.25)
        Behavior on x { NumberAnimation { duration: GlassTheme.normal; easing.type: Easing.OutCubic } }
        Behavior on y { NumberAnimation { duration: GlassTheme.normal; easing.type: Easing.OutCubic } }
        Behavior on width { NumberAnimation { duration: GlassTheme.normal; easing.type: Easing.OutCubic } }
    }
    Flow {
        id: tabs; x: 4; y: 4; width: root.width - 8; spacing: 4
        Repeater {
            id: choices; model: root.labels
            onItemAdded: function(index, delegateItem) { Qt.callLater(root.refreshSelection); }
            Button { objectName: root.namePrefix + index; height: 36 * GlassTheme.scale; label: modelData; quiet: true; emphasized: root.currentIndex === index; selected: false; onClicked: root.selected(index) }
        }
    }
}
