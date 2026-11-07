import QtQuick
import QtQuick.Effects
import "../" as Legacy

/* Băng trượt dưới khối Chơi: slide 0 = Nos Client mới nhất, rồi các slide quảng cáo từ feed
   `promotions.json` (không có thì ẩn). Nút Chơi không nằm trong băng mà ở `HomeHero`, luôn hiện.
   Nút ‹ › và chấm để chuyển; không tự chạy (tránh trượt mất khi đang định bấm). */
Glass {
    id: root
    objectName: "homeSlides"
    property var chosen: null
    property int current: 0
    readonly property var promotions: promotionBridge.slides
    readonly property int count: 1 + promotions.length
    signal playRequested
    signal libraryRequested
    width: parent.width
    height: Math.max(400, nos.contentHeight + 72)
    radius: 26
    padding: 0
    color: GlassTheme.alpha(GlassTheme.selectedSurface, 0.80)
    function go(index) {
        root.current = (index + root.count) % root.count;
        notifier.playUi("nav");
    }

    readonly property bool shaderAvailable: GraphicsInfo.api !== GraphicsInfo.Software && GraphicsInfo.api !== GraphicsInfo.Unknown
    // Cắt theo góc bo: ảnh slide không được tràn ra ngoài khung kính.
    Rectangle { id: roundedMask; width: root.width; height: root.height; radius: root.radius; color: "white"; visible: root.shaderAvailable }
    ShaderEffectSource { id: maskCapture; anchors.fill: parent; sourceItem: roundedMask; hideSource: true; visible: false; live: root.visible && root.shaderAvailable }
    Item {
        id: viewport
        anchors.fill: parent
        clip: true
        layer.enabled: root.shaderAvailable
        layer.effect: MultiEffect { maskEnabled: true; maskSource: maskCapture }
        Row {
            id: track
            x: -root.current * viewport.width
            Behavior on x { NumberAnimation { duration: GlassTheme.reducedMotion ? 0 : 520; easing.type: Easing.OutQuint } }
            NosShowcase {
                id: nos
                width: viewport.width; height: viewport.height
                textInset: 72
                chosen: root.chosen
                active: root.current === 0
                onCreateRequested: root.playRequested()
                onLibraryRequested: root.libraryRequested()
            }
            Repeater {
                model: root.promotions
                PromotionSlide {
                    width: viewport.width; height: viewport.height
                    textInset: 72
                    slide: modelData
                    chosen: root.chosen
                }
            }
        }
    }
    Button {
        objectName: "homeSlidesPrev"
        visible: root.count > 1
        label: "‹"
        width: 42; height: 42
        anchors { left: parent.left; leftMargin: 10; verticalCenter: parent.verticalCenter }
        onClicked: root.go(root.current - 1)
    }
    Button {
        objectName: "homeSlidesNext"
        visible: root.count > 1
        label: "›"
        width: 42; height: 42
        anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
        onClicked: root.go(root.current + 1)
    }
    Row {
        visible: root.count > 1
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 14 }
        spacing: 8
        Repeater {
            model: root.count
            Rectangle {
                width: index === root.current ? 22 : 8; height: 8; radius: 4
                color: index === root.current ? GlassTheme.accent : "#80ffffff"
                Behavior on width { NumberAnimation { duration: 200 } }
                TapHandler { onTapped: root.go(index) }
            }
        }
    }
}
