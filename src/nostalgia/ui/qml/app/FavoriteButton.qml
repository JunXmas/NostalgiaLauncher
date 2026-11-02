import QtQuick
import "../" as Legacy
Button {
    id: root
    property bool favorite: false
    emphasized: favorite
    label: favorite ? "★" : "☆"; quiet: true
    Accessible.name: favorite ? Legacy.Tr.phrase("Bỏ yêu thích") : Legacy.Tr.phrase("Thêm vào yêu thích")
    onFavoriteChanged: { if (!GlassTheme.reducedMotion && visible) pop.restart(); }
    SequentialAnimation {
        id: pop
        NumberAnimation { target: root; property: "rotation"; to: -12; duration: GlassTheme.quick / 2 }
        NumberAnimation { target: root; property: "rotation"; to: 10; duration: GlassTheme.quick }
        NumberAnimation { target: root; property: "rotation"; to: 0; duration: GlassTheme.quick }
    }
    Connections { target: GlassTheme; function onReducedMotionChanged() { if (GlassTheme.reducedMotion) { pop.stop(); root.rotation = 0; } } }
    Rectangle {
        anchors.centerIn: parent; width: parent.width; height: width; radius: width / 2
        color: "transparent"; border.color: GlassTheme.accent; opacity: 0; scale: 0.5
        SequentialAnimation on opacity { running: root.favorite && !GlassTheme.reducedMotion; NumberAnimation { from: 0.65; to: 0; duration: 420 } }
        NumberAnimation on scale { running: root.favorite && !GlassTheme.reducedMotion; from: 0.5; to: 1.35; duration: 420; easing.type: Easing.OutCubic }
    }
}
