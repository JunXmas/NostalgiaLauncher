import QtQuick
import QtQuick.Window
import "GuideCatalog.js" as Guides

WorkspaceDialog {
    id: root
    objectName: "guideDialog"
    property string topicId: "start"
    readonly property var topic: Guides.find(topicId)
    property string query: ""
    property var returnFocus: null
    title: "Cách dùng · " + topic.title
    description: "Các bước ngắn, minh họa ngay trên launcher. Không thực hiện thay đổi khi xem hướng dẫn."
    preferredWidth: 900; preferredHeight: 780
    z: 1000
    function openFor(topicId) {
        if (!opened) {
            var window = root.contentItem.Window.window;
            returnFocus = window ? window.activeFocusItem : null;
        }
        root.topicId = Guides.find(topicId).id; query = ""; open();
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
                Select { objectName: "guideTopicPicker"; width: Math.max(220, (parent.width - 10) / 2); model: Guides.topics.map(function(topic) { return topic.title; }); currentIndex: Guides.topics.findIndex(function(topic) { return topic.id === root.topicId; }); onActivated: function(index) { root.topicId = Guides.topics[index].id; guideScroll.contentY = 0; } }
                Input { objectName: "guideSearch"; width: Math.max(220, (parent.width - 10) / 2); placeholder: "Tìm hướng dẫn…"; text: root.query; onTextChanged: root.query = text }
            }
            Flow {
                visible: !!root.query
                width: parent.width; spacing: 6
                Repeater {
                    model: Guides.topics.filter(function(topic) { return Guides.matches(topic, root.query); })
                    Button { objectName: "guideTopic-" + modelData.id; label: modelData.title; selected: root.topicId === modelData.id; quiet: true; height: 32 * GlassTheme.scale; onClicked: { root.topicId = modelData.id; guideScroll.contentY = 0; } }
                }
            }
            PaymentText { width: parent.width; text: root.topic.summary; color: GlassTheme.muted }
            Grid {
                id: walkthrough; width: parent.width; columns: width > 700 ? 2 : 1; spacing: 18
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
            PaymentText { width: parent.width; text: "GIF minh họa · Tài khoản, modpack và giao dịch trong ảnh là dữ liệu ví dụ."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
            Glass {
                width: parent.width; height: note.implicitHeight + 28; padding: 14; frosted: false
                PaymentText { id: note; width: parent.width; text: root.topic.tip; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
            }
        }
    }
    footer: Flow {
        width: root.bodyWidth; spacing: 10
        Button { label: "Đã hiểu"; primary: true; onClicked: root.close() }
        Button { objectName: "guidePause"; visible: guideMedia.ready && !GlassTheme.reducedMotion; label: guideMedia.paused ? "Phát GIF" : "Tạm dừng GIF"; quiet: true; onClicked: guideMedia.paused = !guideMedia.paused }
    }
}
