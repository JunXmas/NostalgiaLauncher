import QtQuick
import "../" as Legacy

Column {
    width: parent.width
    spacing: 10
    visible: socialBridge.signedIn && !!socialBridge.account.profilePlus
    PaymentText { width: parent.width; text: Legacy.Tr.phrase("HỒ SƠ PLUS"); color: GlassTheme.accent; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
    Flow {
        width: parent.width; spacing: 8
        Repeater {
            model: [{name:"amethyst",label:Legacy.Tr.phrase("Thạch anh"),color:"#b66ba9"},{name:"emerald",label:Legacy.Tr.phrase("Lục bảo"),color:"#60ae7b"},{name:"amber",label:Legacy.Tr.phrase("Hổ phách"),color:"#daa86c"}]
            Button { objectName: "profileAccent-" + modelData.name; label: modelData.label; selected: socialBridge.account.accent === modelData.name; clickable: !socialBridge.busy; onClicked: socialBridge.setProfile(modelData.name,socialBridge.account.showBadge); Rectangle { x: 10; y: 7; width: 5; height: 5; radius: 3; color: modelData.color } }
        }
    }
    Flow {
        width: parent.width; spacing: 8
        Button { objectName: "profileBadgeToggle"; label: socialBridge.account.showBadge ? Legacy.Tr.phrase("Ẩn huy hiệu") : Legacy.Tr.phrase("Hiện huy hiệu"); quiet: true; clickable: !socialBridge.busy; onClicked: socialBridge.setProfile(socialBridge.account.accent || "amethyst",!socialBridge.account.showBadge) }
        Button { objectName: "earlyPreviewDownload"; visible: !!socialBridge.account.earlyPreview; label: Legacy.Tr.phrase("Tải preview sớm  ↗"); quiet: true; clickable: !socialBridge.busy; onClicked: socialBridge.downloadEarlyPreview() }
    }
}
