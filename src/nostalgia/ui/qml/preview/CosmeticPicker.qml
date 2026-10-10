import QtQuick
import "../" as Legacy
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
        PaymentText { width: parent.width - reset.width - parent.spacing; text: Legacy.Tr.phrase("Diện mạo hồ sơ"); font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
        Button { id: reset; objectName: "profileDecor-none"; label: Legacy.Tr.phrase("Nguyên bản"); selected: root.selectedDecor === "none"; quiet: true; onClicked: root.chosen("none") }
    }
    InertialGrid {
        id: options
        objectName: "cosmeticOptionsGrid"
        width: parent.width
        cellWidth: Math.max(1, Math.floor(width / root.columns))
        cellHeight: 180 * GlassTheme.scale + 10
        height: Math.min(Math.ceil(count / root.columns) * cellHeight, 440 * GlassTheme.scale)
        model: Cosmetics.available(cosmeticBridge.sets)
        delegate: Item {
            required property var modelData
            width: options.cellWidth; height: options.cellHeight
            CosmeticOption {
                objectName: "profileDecor-" + parent.modelData.key
                width: parent.width - 10; height: parent.height - 10
                cosmetic: parent.modelData; selected: root.selectedDecor === cosmetic.key
                previewed: root.previewDecor === cosmetic.key; canEquip: root.canEquip || root.ownedCosmetics.indexOf(cosmetic.key) >= 0
                avatarSource: root.avatarSource; playerName: root.playerName
                onClicked: root.chosen(cosmetic.key)
            }
        }
    }
    PaymentText {
        width: parent.width
        text: root.canEquip ? Legacy.Tr.phrase("Chọn một bộ gồm khung avatar và nền hồ sơ. Bạn có thể đổi bộ bất cứ lúc nào.")
            : root.ownedCosmetics.indexOf(root.previewDecor) >= 0 ? Legacy.Tr.phrase("Bộ cosmetic này đã được tặng cho bạn. Có thể sử dụng mà không cần Premium.")
            : root.previewDecor !== root.selectedDecor ? Legacy.Tr.phrase("Đang xem thử ") + Cosmetics.name(root.previewDecor, cosmeticBridge.sets) + Legacy.Tr.phrase(". Hồ sơ đã lưu vẫn giữ nguyên; cần Plus trở lên để áp dụng.")
            : Legacy.Tr.phrase("Có thể xem thử mọi bộ. Dùng cosmetic được tặng hoặc mở Plus để chọn các bộ còn lại.")
        color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption
    }
}
