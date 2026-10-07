import QtQuick

Rectangle {
    property string badge: ""
    width: badgeText.implicitWidth + 24; height: badgeText.implicitHeight + 12
    radius: 9; color: GlassTheme.alpha(GlassTheme.accent, 0.15)
    border.color: GlassTheme.alpha(GlassTheme.accent, 0.30)
    PaymentText { id: badgeText; anchors.centerIn: parent; text: "✦  " + parent.badge; color: GlassTheme.accent; font.pixelSize: GlassTheme.fontCaption; font.weight: Font.DemiBold }
    Accessible.name: "Huy hiệu " + badge
}
