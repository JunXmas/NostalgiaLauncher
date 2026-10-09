import QtQuick
import "CosmeticCatalog.js" as Cosmetics

Column {
    id: root
    property string selectedDecor: "none"
    property string previewDecor: "none"
    property string avatarSource: ""
    property string playerName: ""
    property bool canEquip: false
    property var ownedCosmetics: []
    signal chosen(string decor)
    readonly property int columns: width >= 540 * GlassTheme.scale ? 3 : width >= 350 * GlassTheme.scale ? 2 : 1
    spacing: 12
    Row { width: parent.width; spacing: 12
        PaymentText { width: parent.width - reset.width - parent.spacing; text: "Diện mạo hồ sơ"; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
        Button { id: reset; objectName: "profileDecor-none"; label: "Nguyên bản"; selected: root.selectedDecor === "none"; quiet: true; onClicked: root.chosen("none") }
    }
    Flow { width: parent.width; spacing: 10
        Repeater { model: Cosmetics.available(cosmeticBridge.sets)
            CosmeticOption {
                objectName: "profileDecor-" + modelData.key
                width: (root.width - 10 * (root.columns - 1)) / root.columns
                cosmetic: modelData; selected: root.selectedDecor === modelData.key
                previewed: root.previewDecor === modelData.key; canEquip: root.canEquip || root.ownedCosmetics.indexOf(modelData.key) >= 0
                avatarSource: root.avatarSource; playerName: root.playerName
                onClicked: root.chosen(modelData.key)
            }
        }
    }
    PaymentText {
        width: parent.width
        text: root.canEquip ? "Chọn một bộ gồm khung avatar và nền hồ sơ. Bạn có thể đổi bộ bất cứ lúc nào."
            : root.ownedCosmetics.indexOf(root.previewDecor) >= 0 ? "Bộ cosmetic này đã được tặng cho bạn. Có thể sử dụng mà không cần Premium."
            : root.previewDecor !== root.selectedDecor ? "Đang xem thử " + Cosmetics.name(root.previewDecor, cosmeticBridge.sets) + ". Hồ sơ đã lưu vẫn giữ nguyên; cần Plus trở lên để áp dụng."
            : "Có thể xem thử mọi bộ. Dùng cosmetic được tặng hoặc mở Plus để chọn các bộ còn lại."
        color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption
    }
}
