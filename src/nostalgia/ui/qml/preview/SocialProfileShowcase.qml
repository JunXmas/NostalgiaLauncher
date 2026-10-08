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
                PaymentText { text: "SKIN"; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
                PaymentText { width: parent.width; text: profile.skinFile ? "Diện mạo trong Minecraft" : "Chưa chia sẻ skin"; font.pixelSize: GlassTheme.fontSubheading; font.weight: Font.DemiBold }
                PaymentText { width: parent.width; visible: !!profile.skinFile; text: "Kéo để xoay nhân vật."; color: GlassTheme.muted }
            }
            Legacy.SkinFigure { objectName: "profileSkin3D"; anchors.right: parent.right; height: skinArea.height; width: height / 2; anchors.rightMargin: parent.width * 0.10; source: profile.skinFile || ""; slim: details.slim === true; visible: !!source; renderEnabled: visible; interactive: true }
        }
    }
    PaymentText { text: "COSMETIC HỒ SƠ"; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
    PaymentText { width: parent.width; text: Cosmetics.find(details.decor, cosmeticBridge.sets) ? Cosmetics.name(details.decor, cosmeticBridge.sets) + " · Khung avatar và nền hồ sơ" : "Phong cách nguyên bản"; font.weight: Font.DemiBold }
    PaymentText { text: "MODPACK HAY CHƠI"; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
    Repeater { model: details.favorite_packs || []
        Glass { width: parent.width; padding: 16; height: packBody.implicitHeight + 32
            Column { id: packBody; width: parent.width; spacing: 6
                PaymentText { width: parent.width; text: modelData.title; font.weight: Font.DemiBold }
                PaymentText { width: parent.width; text: modelData.game_version; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
            }
        }
    }
    PaymentText { width: parent.width; visible: !(details.favorite_packs || []).length; text: "Chưa chọn modpack để chia sẻ."; color: GlassTheme.muted }
}
