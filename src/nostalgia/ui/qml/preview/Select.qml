import QtQuick
import "../" as Legacy
import QtQuick.Window
import QtQuick.Controls as Controls

Controls.ComboBox {
    id: root
    height: 42 * GlassTheme.scale
    font.family: GlassTheme.font
    font.pixelSize: GlassTheme.fontBody
    property string searchText: ""
    property bool consumeChoiceRelease: false
    property string searchPlaceholder: Legacy.Tr.phrase("Tìm trong danh sách…")
    property Item menuBackdrop: GlassTheme.backdrop
    readonly property bool searchable: count > 8
    readonly property var filteredChoices: {
        var choices = [];
        var source = root.model;
        var query = searchText.trim().toLowerCase();
        for (var i = 0; source && i < count; i++) {
            var label = textAt(i);
            if (!query || label.toLowerCase().indexOf(query) >= 0)
                choices.push({label: label, sourceIndex: i});
        }
        return choices;
    }
    function choose(index, keyboard) {
        if (index < 0 || index >= filteredChoices.length)
            return;
        currentIndex = filteredChoices[index].sourceIndex;
        consumeChoiceRelease = keyboard === true;
        activated(currentIndex);
        popup.close();
        forceActiveFocus();
    }
    Keys.onReleased: function (event) {
        if (consumeChoiceRelease && (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space)) {
            consumeChoiceRelease = false;
            event.accepted = true;
        }
    }
    background: Rectangle {
        radius: 12
        color: GlassTheme.alpha(GlassTheme.raised, 0.40)
        border.color: root.activeFocus ? GlassTheme.accent : GlassTheme.stroke
    }
    contentItem: Text {
        leftPadding: 14
        rightPadding: 30
        verticalAlignment: Text.AlignVCenter
        text: root.displayText
        color: root.enabled ? GlassTheme.text : GlassTheme.muted
        font: root.font
        elide: Text.ElideRight
    }
    indicator: Text {
        x: root.width - 26
        anchors.verticalCenter: parent.verticalCenter
        text: "⌄"
        color: GlassTheme.muted
        font.pixelSize: GlassTheme.fontAction
        rotation: root.popup.visible ? 180 : 0
        Behavior on rotation { NumberAnimation { duration: GlassTheme.quick; easing.type: Easing.OutCubic } }
    }
    popup: Controls.Popup {
        id: menu
        objectName: root.objectName + "Menu"
        y: root.height + 6
        width: root.searchable ? Math.max(root.width, Math.min(240 * GlassTheme.scale, root.Window.window ? root.Window.window.width - 24 : root.width)) : root.width
        padding: 8
        margins: 12
        readonly property real rowHeight: 34 * GlassTheme.scale
        readonly property real searchHeight: root.searchable ? 44 * GlassTheme.scale : 0
        height: Math.min(Math.max(1, root.count) * rowHeight + searchHeight + 16, 6 * rowHeight + searchHeight + 16,
            root.Window.window ? root.Window.window.height * 0.48 : 320 * GlassTheme.scale)
        closePolicy: Controls.Popup.CloseOnEscape | Controls.Popup.CloseOnPressOutsideParent
        onAboutToShow: {
            root.searchText = "";
            choices.currentIndex = choices.count ? Math.max(0, root.filteredChoices.findIndex(function (choice) { return choice.sourceIndex === root.currentIndex; })) : -1;
            choices.positionViewAtIndex(Math.max(0, choices.currentIndex), ListView.Contain);
        }
        onOpened: {
            if (root.searchable) search.forceActiveFocus();
            else choices.forceActiveFocus();
        }
        onClosed: { menuMotion.stopMotion(); root.searchText = ""; }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.quick } }
        exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: GlassTheme.quick } }
        background: Glass {
            id: menuGlass
            objectName: root.objectName + "MenuMica"
            clip: true
            padding: 0; radius: 14
            color: "transparent"
            backdrop: root.menuBackdrop
            backdropRect: {
                if (!menu.visible || !root.menuBackdrop || !menuGlass.parent || !menuGlass.parent.parent)
                    return Qt.rect(0, 0, 1, 1);
                // Track the popup frame's final position, including upward placement.
                var frame = menuGlass.parent;
                var origin = frame.parent.mapToItem(root.menuBackdrop.parent,
                    frame.x + menuGlass.x, frame.y + menuGlass.y);
                return Qt.rect(origin.x - root.menuBackdrop.x, origin.y - root.menuBackdrop.y,
                    menu.width, menu.height);
            }
            frosted: menu.visible
            blurRadius: 48; blurOpacity: 0.95; finishOpacity: 0.45
            Rectangle {
                anchors.fill: parent
                radius: menuGlass.radius
                color: GlassTheme.alpha(GlassTheme.surface, menuGlass.shaderAvailable ? 0.68 : 0.96)
                border.color: GlassTheme.stroke
            }
        }
        contentItem: Item {
            Controls.TextField {
                id: search
                objectName: root.objectName + "Search"
                width: parent.width
                height: Math.max(0, menu.searchHeight - 4)
                visible: root.searchable
                placeholderText: root.searchPlaceholder
                text: root.searchText
                onTextChanged: { root.searchText = text; choices.currentIndex = choices.count ? 0 : -1; }
                font: root.font
                color: GlassTheme.text
                placeholderTextColor: GlassTheme.muted
                selectByMouse: true
                background: Rectangle { radius: 8; color: GlassTheme.alpha(GlassTheme.raised, 0.35); border.color: GlassTheme.stroke }
                Keys.onDownPressed: choices.currentIndex = Math.min(choices.count - 1, choices.currentIndex + 1)
                Keys.onUpPressed: choices.currentIndex = Math.max(0, choices.currentIndex - 1)
                Keys.onReturnPressed: root.choose(choices.currentIndex, true)
                Keys.onEnterPressed: root.choose(choices.currentIndex, true)
            }
            ListView {
                id: choices
                objectName: root.objectName + "Choices"
                anchors.top: search.visible ? search.bottom : parent.top
                anchors.topMargin: search.visible ? 4 : 0
                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                clip: true
                model: root.filteredChoices
                boundsBehavior: Flickable.StopAtBounds
                keyNavigationEnabled: true
                Keys.onDownPressed: currentIndex = Math.min(count - 1, currentIndex + 1)
                Keys.onUpPressed: currentIndex = Math.max(0, currentIndex - 1)
                Keys.onReturnPressed: root.choose(currentIndex, true)
                Keys.onEnterPressed: root.choose(currentIndex, true)
                delegate: Controls.ItemDelegate {
                    required property var modelData
                    required property int index
                    width: choices.width; height: menu.rowHeight
                    highlighted: hovered || choices.currentIndex === index
                    onClicked: root.choose(index)
                    Keys.onReturnPressed: root.choose(choices.currentIndex, true)
                    Keys.onEnterPressed: root.choose(choices.currentIndex, true)
                    Keys.onSpacePressed: root.choose(choices.currentIndex, true)
                    contentItem: Text {
                        text: modelData.label
                        color: modelData.sourceIndex === root.currentIndex ? GlassTheme.accent : GlassTheme.text
                        font: root.font
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: highlighted ? GlassTheme.alpha(GlassTheme.accent, 0.16) : "transparent"
                        radius: 8
                    }
                }
                InertialMotion { id: menuMotion; objectName: root.objectName + "Motion"; target: choices; enabled: menu.visible }
                Controls.ScrollBar.vertical: Controls.ScrollBar { policy: choices.contentHeight > choices.height ? Controls.ScrollBar.AsNeeded : Controls.ScrollBar.AlwaysOff; onPressedChanged: if (pressed) menuMotion.stopMotion() }
            }
            Text {
                anchors.centerIn: choices
                visible: !choices.count
                text: Legacy.Tr.phrase("Không tìm thấy phiên bản")
                color: GlassTheme.muted; font: root.font
            }
        }
    }
}
