import QtQuick
import "../" as Legacy

Column {
    id: root
    spacing: 8
    property bool directAllowed: true
    property bool expanded: false
    property string toggleName: ""
    signal preferenceChanged(bool allowed)

    PaymentText {
        width: parent.width
        text: root.directAllowed
            ? Legacy.Tr.phrase("Tự động · P2P có mã hoá, relay dự phòng")
            : Legacy.Tr.phrase("Kết nối qua relay")
        font.weight: Font.DemiBold
        font.pixelSize: GlassTheme.fontCaption
    }
    PaymentText {
        width: parent.width
        text: root.directAllowed
            ? Legacy.Tr.phrase("P2P có thể chia sẻ IP với người cùng phòng. Launcher tự dùng relay nếu không kết nối trực tiếp được.")
            : Legacy.Tr.phrase("Chỉ dùng relay để tránh chia sẻ IP trực tiếp với người cùng phòng.")
        color: GlassTheme.muted
        font.pixelSize: GlassTheme.fontCaption
    }
    Button {
        objectName: root.toggleName + "Options"
        label: root.expanded ? Legacy.Tr.phrase("Thu gọn tùy chọn kết nối") : Legacy.Tr.phrase("Tùy chọn kết nối")
        quiet: true
        onClicked: root.expanded = !root.expanded
    }
    Legacy.CheckRow {
        objectName: root.toggleName
        width: parent.width
        visible: root.expanded
        label: Legacy.Tr.phrase("Ưu tiên kết nối trực tiếp có mã hoá")
        checked: root.directAllowed
        onToggled: function(checked) { root.preferenceChanged(checked); }
    }
}
