import QtQuick
import "CosmeticCatalog.js" as Cosmetics

Column {
    id: root
    property string selectedDecor: "none"
    property string previewDecor: "none"
    property string avatarSource: ""
    property string playerName: ""
    property bool canEquip: false
    signal chosen(string decor)
    readonly property int columns: width >= 540 * GlassTheme.scale ? 3 : width >= 350 * GlassTheme.scale ? 2 : 1
    spacing: 12
    Row { width: parent.width; spacing: 12
        PaymentText { width: parent.width - reset.width - parent.spacing; text: "Diện mạo hồ sơ"; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
        Button { id: reset; objectName: "profileDecor-none"; label: "Nguyên bản"; selected: root.selectedDecor === "none"; quiet: true; onClicked: root.chosen("none") }
    }
    Flow { width: parent.width; spacing: 10
        Repeater { model: Cosmetics.sets
            CosmeticOption {
                objectName: "profileDecor-" + modelData.key
                width: (root.width - 10 * (root.columns - 1)) / root.columns
                cosmetic: modelData; selected: root.selectedDecor === modelData.key
                previewed: root.previewDecor === modelData.key; canEquip: root.canEquip
                avatarSource: root.avatarSource; playerName: root.playerName
                onClicked: root.chosen(modelData.key)
            }
        }
    }
    PaymentText {
        width: parent.width; visible: !root.canEquip
        text: root.previewDecor !== root.selectedDecor ? "Đang xem thử " + Cosmetics.name(root.previewDecor) + ". Hồ sơ đã lưu vẫn giữ nguyên; cần Pro trở lên để áp dụng." : "Có thể xem thử mọi bộ. Quyền áp dụng dành cho Pro trở lên và hiện đang tạm tắt cùng các tính năng trả phí."
        color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption
    }
}
