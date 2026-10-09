import QtQuick
import "preview" as Preview

Item {
    id: root
    property var shown: ({})
    property var viewport: null
    readonly property var draft: skinEditor.details
    readonly property bool microsoft: shown.accountKind === "microsoft"
    readonly property var capes: microsoft && capeBridge.loadedFor === shown.accountId ? capeBridge.capes : []
    implicitHeight: grid.implicitHeight + (notice.visible ? notice.implicitHeight + 12 : 0)
    onVisibleChanged: if (visible && shown.accountId) capeBridge.loadCapes(shown.accountId)
    onShownChanged: if (visible && shown.accountId) capeBridge.loadCapes(shown.accountId)
    Flow {
        id: grid; width: parent.width; spacing: 12
        Repeater {
            model: root.capes
            Preview.Glass {
                id: card
                objectName: "capeCard-" + modelData.capeId
                width: 156 * Theme.textScale; height: 250 * Theme.textScale; padding: 12
                border.color: root.draft.capeId === modelData.capeId ? Theme.accent : Theme.border
                readonly property bool inViewport: !root.viewport || y + root.y - root.viewport.contentY + height > 0 && y + root.y - root.viewport.contentY < root.viewport.height
                SkinFigure {
                    objectName: "capeLibraryFigure"
                    anchors.top: parent.top; anchors.horizontalCenter: parent.horizontalCenter
                    width: 78 * Theme.textScale; height: width * 2; interactive: false
                    source: root.draft.source || ""; slim: root.draft.slim || false
                    capeSource: modelData.textureFile || ""; previewFrame: 41
                    renderEnabled: card.inViewport
                }
                Column {
                    anchors.bottom: parent.bottom; width: parent.width; spacing: 6
                    Preview.PaymentText { width: parent.width; text: modelData.alias; maximumLineCount: 1; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter; font.weight: Font.DemiBold }
                    Preview.Button {
                        objectName: "previewCape-" + modelData.capeId
                        width: parent.width; height: 32
                        label: root.draft.capeId === modelData.capeId ? "Đang xem trước" : "Thử cape"
                        selected: root.draft.capeId === modelData.capeId
                        clickable: !skinEditor.busy && !!modelData.textureFile
                        onClicked: skinEditor.selectCape(modelData.capeId)
                    }
                }
                scale: hover.hovered ? 1.02 : 1
                Behavior on scale { NumberAnimation { duration: Theme.quick } }
                HoverHandler { id: hover }
            }
        }
        Preview.Button { objectName: "previewNoCape"; visible: root.microsoft && root.capes.length > 0; label: "Không mặc cape"; selected: root.draft.capeId === ""; clickable: !skinEditor.busy; onClicked: skinEditor.selectCape("") }
        Preview.Glass {
            width: 156 * Theme.textScale; height: 220 * Theme.textScale; padding: 12
            visible: !root.microsoft && !!root.shown.capeFile
            SkinFigure { anchors.centerIn: parent; width: 82 * Theme.textScale; height: width * 2; interactive: false; source: root.draft.source || ""; slim: root.draft.slim || false; capeSource: root.shown.capeFile || ""; previewFrame: 41; revision: (root.draft.entryId || "") + "|" + (root.shown.capeDigest || "") }
        }
    }
    Preview.PaymentText {
        id: notice; anchors.top: grid.bottom; anchors.topMargin: 12; width: parent.width
        visible: root.capes.length === 0 && !root.shown.capeFile
        text: capeBridge.busy ? "Đang tải cape…" : "Chưa có áo choàng."
        color: Theme.textMuted
    }
}
