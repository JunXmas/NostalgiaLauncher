import QtQuick
import QtQuick.Effects
import "../" as Legacy

/* Băng trượt đầu trang chủ: slide 0 = Nos Client mới nhất, slide 1 = server Forgotten Worlds,
   slide 2 = bản chơi của bạn. Nút ‹ › và chấm để chuyển; không tự chạy (tránh trượt mất khi đang
   định bấm). */
Glass {
    id: root
    objectName: "homeSlides"
    property var chosen: null
    property int current: 0
    readonly property int count: 3
    signal playRequested
    signal libraryRequested
    signal createServerRequested
    width: parent.width
    height: Math.max(400, heroCopy.implicitHeight + 72 * 2, showcase.contentHeight + 64, nos.contentHeight + 72)
    readonly property Item heroCopy: hero.contentItem
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
            ServerShowcase {
                id: showcase
                width: viewport.width; height: viewport.height
                textInset: 72
                active: root.current === 1
                onCreateRequested: root.createServerRequested()
            }
            HomeHero {
                id: hero
                width: viewport.width; height: viewport.height
                chosen: root.chosen
                color: "transparent"
                frosted: false
                border.width: 0
                radius: 0
                padding: 72
                onPlayRequested: root.playRequested()
                onLibraryRequested: root.libraryRequested()
            }
        }
    }
    Button {
        objectName: "homeSlidesPrev"
        label: "‹"
        width: 42; height: 42
        anchors { left: parent.left; leftMargin: 10; verticalCenter: parent.verticalCenter }
        onClicked: root.go(root.current - 1)
    }
    Button {
        objectName: "homeSlidesNext"
        label: "›"
        width: 42; height: 42
        anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
        onClicked: root.go(root.current + 1)
    }
    Row {
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
