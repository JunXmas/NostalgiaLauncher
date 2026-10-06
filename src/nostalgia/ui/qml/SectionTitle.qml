import QtQuick
Text {
    property string caption: ""
    text: caption
    color: Theme.text
    font.pixelSize: Theme.fontHeading
    font.bold: true
    Accessible.role: Accessible.Heading
    Accessible.name: caption
}
