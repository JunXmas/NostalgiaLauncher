import QtQuick

PaymentText {
    property string reason: ""
    text: reason
    visible: !!reason
    textFormat: Text.PlainText
    color: GlassTheme.muted
    font.pixelSize: GlassTheme.fontLabel
}
