import QtQuick
import "../" as Legacy
Flow {
    id: root
    property var products: []
    property string selectedId: ""
    signal chosen(var product)
    spacing: 12
    Repeater {
        model: root.products
        delegate: Glass { padding: 0;
            required property var modelData
            width: Math.max(180, (root.width-12)/2); height: 176
            Button { objectName: "marketProduct-"+modelData.product_id; anchors.fill: parent; label: ""; quiet: true; selected: root.selectedId === modelData.product_id; Accessible.name: (Legacy.Tr.currentLanguage === "vi" ? modelData.name_vi : modelData.name_en)+", "+modelData.price+" coin"; onClicked: root.chosen(modelData) }
            Rectangle { x: 16; y: 16; width: 90; height: 48; radius: 14; color: Legacy.Theme.mix(GlassTheme.raised, GlassTheme.accent, 0.25)
                PaymentText { anchors.centerIn: parent; text: modelData.product_kind === "bundle" ? Legacy.Tr.phrase("Bộ") : Legacy.Tr.phrase(modelData.slot); font.pixelSize: GlassTheme.fontCaption; color: GlassTheme.text }
            }
            Column { x: 16; y: 76; width: parent.width-32; spacing: 6
                PaymentText { width: parent.width; text: Legacy.Tr.currentLanguage === "vi" ? modelData.name_vi : modelData.name_en; font.weight: Font.DemiBold; elide: Text.ElideRight }
                PaymentText { text: modelData.price + " coin"; color: GlassTheme.accent }
            }

        }
    }
}
