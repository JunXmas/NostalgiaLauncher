import QtQuick
Item {
    id: root
    property string provider: ""
    implicitWidth: 22; implicitHeight: 22
    readonly property bool ready: logo.status === Image.Ready
    Image {
        id: logo
        objectName: "providerLogo-" + root.provider
        anchors.fill: parent; asynchronous: true; cache: true
        source: root.provider === "google" ? "../assets/providers/google.png" : root.provider === "microsoft" ? "../assets/providers/microsoft.svg" : ""
        fillMode: Image.PreserveAspectFit
    }
}
