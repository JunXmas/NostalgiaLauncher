import QtQuick
import "../" as Legacy

Column {
    id: root
    spacing: 8
    PaymentText {
        objectName: "p2pOnlyStatus"
        width: parent.width
        text: Legacy.Tr.phrase("P2P có mã hoá · Relay dữ liệu đã tắt")
        font.weight: Font.DemiBold
        font.pixelSize: GlassTheme.fontCaption
    }
    PaymentText {
        width: parent.width
        text: Legacy.Tr.phrase("Dữ liệu game và modpack đi trực tiếp giữa hai máy. Người cùng phòng có thể biết IP của bạn. Nếu mạng chặn P2P, hãy thử mạng khác.")
        color: GlassTheme.muted
        font.pixelSize: GlassTheme.fontCaption
    }
}
