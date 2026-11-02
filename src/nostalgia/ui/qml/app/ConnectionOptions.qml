import QtQuick
import "../" as Legacy

PaymentText {
    objectName: "p2pPrivacyNote"
    text: Legacy.Tr.phrase("Hai máy nối thẳng với nhau, người cùng phòng có thể thấy IP của bạn.")
    color: GlassTheme.muted
    font.pixelSize: GlassTheme.fontCaption
}
