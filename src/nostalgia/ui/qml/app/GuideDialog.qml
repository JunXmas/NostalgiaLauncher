import QtQuick
import "../" as Legacy
import QtQuick.Window
import "GuideCatalog.js" as Guides

WorkspaceDialog {
    id: root
    objectName: "guideDialog"
    property string topicId: "start"
    readonly property var topic: Guides.find(topicId, Legacy.Tr)
    property string query: ""
    property var returnFocus: null
    title: Legacy.Tr.phrase("Cách dùng · ") + topic.title
    description: Legacy.Tr.phrase("Các bước ngắn, minh họa ngay trên launcher. Không thực hiện thay đổi khi xem hướng dẫn.")
    preferredWidth: 900; preferredHeight: 780
    z: 1000
    function openFor(topicId) {
        if (!opened) {
            var window = root.contentItem.Window.window;
            returnFocus = window ? window.activeFocusItem : null;
        }
        root.topicId = Guides.find(topicId, Legacy.Tr).id; query = ""; open();
    }
    onClosed: Qt.callLater(function() { if (root.returnFocus && root.returnFocus.visible && root.returnFocus.enabled) root.returnFocus.forceActiveFocus(); })
    Connections { target: GuideCenter; function onRequested(topicId, opener) { root.openFor(topicId); if (opener) root.returnFocus = opener; } }
    InertialScroll {
        id: guideScroll; objectName: "guideScroll"
        anchors.fill: parent; contentHeight: contents.implicitHeight + 8
        Column {
            id: contents; width: parent.width - 10; spacing: 16
            Flow {
                width: parent.width; spacing: 10
                readonly property real fieldWidth: width >= 600 * GlassTheme.scale ? (width - spacing) / 2 : width
                Select { objectName: "guideTopicPicker"; width: parent.fieldWidth; model: Guides.topics.map(function(topic) { return Legacy.Tr.phrase(topic.title); }); currentIndex: Guides.topics.findIndex(function(topic) { return topic.id === root.topicId; }); onActivated: function(index) { root.topicId = Guides.topics[index].id; guideScroll.contentY = 0; } }
                Input { objectName: "guideSearch"; width: parent.fieldWidth; placeholder: Legacy.Tr.phrase("Tìm hướng dẫn…"); text: root.query; onTextChanged: root.query = text }
            }
            Flow {
                visible: !!root.query
                width: parent.width; spacing: 6
                Repeater {
                    model: Guides.topics.filter(function(topic) { return Guides.matches(Guides.find(topic.id, Legacy.Tr), root.query); })
                    Button { objectName: "guideTopic-" + modelData.id; label: Legacy.Tr.phrase(modelData.title); selected: root.topicId === modelData.id; quiet: true; height: 32 * GlassTheme.scale; onClicked: { root.topicId = modelData.id; guideScroll.contentY = 0; } }
                }
            }
            PaymentText { width: parent.width; text: root.topic.summary; color: GlassTheme.muted }
            Grid {
                id: walkthrough; objectName: "guideWalkthrough"; width: parent.width; columns: width >= 760 * GlassTheme.scale ? 2 : 1; spacing: 18
                GuideMedia { id: guideMedia; width: walkthrough.columns === 2 ? (walkthrough.width - walkthrough.spacing) * 0.54 : walkthrough.width; height: Math.min(340, width * 0.75); clipName: root.topic.clip; active: root.opened }
                Column {
                    width: walkthrough.columns === 2 ? (walkthrough.width - walkthrough.spacing) * 0.46 : walkthrough.width; spacing: 16
                    Repeater {
                        model: root.topic.steps
                        Row {
                            width: parent.width; spacing: 12
                            Rectangle {
                                width: 28; height: 28; radius: 9; color: GlassTheme.selectedSurface
                                PaymentText { anchors.centerIn: parent; text: String(index + 1); color: GlassTheme.accent; font.weight: Font.DemiBold }
                            }
                            PaymentText { width: parent.width - 40; text: modelData; font.pixelSize: GlassTheme.fontBody }
                        }
                    }
                }
            }
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("GIF minh họa · Tài khoản, modpack và giao dịch trong ảnh là dữ liệu ví dụ."); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
            Glass {
                objectName: "guideTipSurface"
                width: parent.width; height: note.implicitHeight + 28; padding: 14; frosted: false
                PaymentText { id: note; width: parent.width; text: root.topic.tip; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
            }
        }
    }
    footer: Flow {
        width: root.bodyWidth; spacing: 10
        Button { label: Legacy.Tr.phrase("Đã hiểu"); primary: true; onClicked: root.close() }
        Button { objectName: "guidePause"; visible: guideMedia.ready && !GlassTheme.reducedMotion; label: guideMedia.paused ? Legacy.Tr.phrase("Phát GIF") : Legacy.Tr.phrase("Tạm dừng GIF"); quiet: true; onClicked: guideMedia.paused = !guideMedia.paused }
    }
}
