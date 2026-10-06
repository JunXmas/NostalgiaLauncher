import QtQuick

Column {
    width: parent.width
    spacing: 10
    visible: socialBridge.signedIn && !!socialBridge.account.profilePlus
    PaymentText { width: parent.width; text: "HỒ SƠ PLUS"; color: GlassTheme.accent; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
    Flow {
        width: parent.width; spacing: 8
        Repeater {
            model: [{name:"amethyst",label:"Thạch anh",color:"#b66ba9"},{name:"emerald",label:"Lục bảo",color:"#60ae7b"},{name:"amber",label:"Hổ phách",color:"#daa86c"}]
            Button { objectName: "profileAccent-" + modelData.name; label: modelData.label; selected: socialBridge.account.accent === modelData.name; clickable: !socialBridge.busy; onClicked: socialBridge.setProfile(modelData.name,socialBridge.account.showBadge); Rectangle { x: 10; y: 7; width: 5; height: 5; radius: 3; color: modelData.color } }
        }
    }
    Flow {
        width: parent.width; spacing: 8
        Button { objectName: "profileBadgeToggle"; label: socialBridge.account.showBadge ? "Ẩn huy hiệu" : "Hiện huy hiệu"; quiet: true; clickable: !socialBridge.busy; onClicked: socialBridge.setProfile(socialBridge.account.accent || "amethyst",!socialBridge.account.showBadge) }
        Button { objectName: "earlyPreviewDownload"; visible: !!socialBridge.account.earlyPreview; label: "Tải preview sớm  ↗"; quiet: true; clickable: !socialBridge.busy; onClicked: socialBridge.downloadEarlyPreview() }
    }
}
