import QtQuick
import "../" as Legacy
import "CosmeticCatalog.js" as Cosmetics

Column {
    property var profile: ({})
    property var details: ({})
    spacing: 18
    Glass { width: parent.width; padding: 18; height: skinArea.height + 36
        Item { id: skinArea; width: parent.width; height: !!profile.skinFile ? 190 * GlassTheme.scale : 76 * GlassTheme.scale
            Column { width: parent.width * 0.53; spacing: 10
                PaymentText { text: Legacy.Tr.phrase("SKIN"); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
                PaymentText { width: parent.width; text: profile.skinFile ? Legacy.Tr.phrase("Diện mạo trong Minecraft") : Legacy.Tr.phrase("Chưa chia sẻ skin"); font.pixelSize: GlassTheme.fontSubheading; font.weight: Font.DemiBold }
                PaymentText { width: parent.width; visible: !!profile.skinFile; text: Legacy.Tr.phrase("Kéo để xoay nhân vật."); color: GlassTheme.muted }
            }
            Legacy.SkinFigure { objectName: "profileSkin3D"; anchors.right: parent.right; height: skinArea.height; width: height / 2; anchors.rightMargin: parent.width * 0.10; source: profile.skinFile || ""; slim: details.slim === true; visible: !!source; renderEnabled: visible; interactive: true }
        }
    }
    PaymentText { text: Legacy.Tr.phrase("COSMETIC HỒ SƠ"); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
    PaymentText { width: parent.width; text: Cosmetics.find(details.decor, cosmeticBridge.sets) ? Cosmetics.name(details.decor, cosmeticBridge.sets) + Legacy.Tr.phrase(" · Khung avatar và nền hồ sơ") : Legacy.Tr.phrase("Phong cách nguyên bản"); font.weight: Font.DemiBold }
    PaymentText { text: Legacy.Tr.phrase("MODPACK HAY CHƠI"); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
    Repeater { model: details.favorite_packs || []
        Glass { width: parent.width; padding: 16; height: packBody.implicitHeight + 32
            Column { id: packBody; width: parent.width; spacing: 6
                PaymentText { width: parent.width; text: modelData.title; font.weight: Font.DemiBold }
                PaymentText { width: parent.width; text: modelData.game_version; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
            }
        }
    }
    PaymentText { width: parent.width; visible: !(details.favorite_packs || []).length; text: Legacy.Tr.phrase("Chưa chọn modpack để chia sẻ."); color: GlassTheme.muted }
}
