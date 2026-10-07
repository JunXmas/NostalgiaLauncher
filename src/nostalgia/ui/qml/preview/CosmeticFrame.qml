import QtQuick
import "CosmeticCatalog.js" as Cosmetics

Image {
    id: root
    property string decor: "none"
    readonly property bool decorated: !!Cosmetics.find(decor)
    readonly property bool ready: status === Image.Ready
    source: visible && decorated ? Cosmetics.asset(decor, "frame") : ""
    sourceSize: Qt.size(Math.min(384, Math.max(40, Math.ceil(width * Screen.devicePixelRatio))), Math.min(384, Math.max(40, Math.ceil(height * Screen.devicePixelRatio))))
    asynchronous: true
    cache: true
    smooth: true
    fillMode: Image.PreserveAspectFit
}
