import QtQuick
import "../" as Legacy

Column {
    id: root
    property var profile: ({})
    property var details: ({})
    property string skinEntryId: ""
    property string avatarMode: "google"
    property string decor: "none"
    property string previewDecor: "none"
    property bool shareSkin: false
    property var favorites: []
    spacing: 14
    function populate() {
        bio.text = details.bio || ""; avatarMode = details.avatar_mode || "google";
        decor = details.decor || "none"; previewDecor = decor; shareSkin = !!profile.skinFile;
        skinEntryId = ""; favorites = (details.favorite_packs || []).slice();
    }
    function togglePack(pack) {
        var next = favorites.slice();
        var index = next.findIndex(function(p) { return p.title === pack.title && p.game_version === pack.game_version; });
        if (index >= 0) next.splice(index, 1); else if (next.length < 3) next.push(pack);
        favorites = next;
    }
    function save() { profileBridge.save(bio.text, avatarMode, skinEntryId, shareSkin, favorites, decor); }
    CosmeticPicker {
        width: parent.width; selectedDecor: root.decor; previewDecor: root.previewDecor
        avatarSource: root.profile.avatar_url || ""; playerName: root.profile.name || ""
        canEquip: socialBridge.account.cosmeticPlus === true
        ownedCosmetics: root.details.ownedCosmetics || []
        onChosen: function(value) {
            root.previewDecor = value;
            if (value === "none" || canEquip || ownedCosmetics.indexOf(value) >= 0) root.decor = value;
        }
    }
    PaymentText { text: Legacy.Tr.phrase("Giới thiệu"); font.weight: Font.DemiBold }
    Input { id: bio; objectName: "profileBio"; width: parent.width; placeholder: Legacy.Tr.phrase("Một vài lời về bạn · Tối đa 160 ký tự"); maximumLength: 160 }
    PaymentText { text: Legacy.Tr.phrase("Ảnh đại diện"); font.weight: Font.DemiBold }
    Flow { width: parent.width; spacing: 8
        Repeater { model: [{key:"google", title:Legacy.Tr.phrase("Ảnh Google")}, {key:"skin", title:Legacy.Tr.phrase("Mặt skin")}, {key:"initials", title:Legacy.Tr.phrase("Chữ cái")}]
            Button { objectName: "profileAvatarMode-" + modelData.key; label: modelData.title; selected: root.avatarMode === modelData.key; clickable: modelData.key !== "skin" || root.shareSkin; onClicked: root.avatarMode = modelData.key }
        }
    }
    Row { width: parent.width; spacing: 12
        Legacy.Toggle { objectName: "shareProfileSkin"; checked: root.shareSkin; accessibleLabel: Legacy.Tr.phrase("Chia sẻ skin trong hồ sơ"); onToggled: function(value) { root.shareSkin = value; if (!value && root.avatarMode === "skin") root.avatarMode = "google"; } }
        PaymentText { width: parent.width - 70; text: Legacy.Tr.phrase("Hiện skin cho bạn bè"); anchors.verticalCenter: parent.verticalCenter }
    }
    Select { objectName: "profileSkinChoice"; width: parent.width; visible: root.shareSkin; model: [root.profile.skinFile ? Legacy.Tr.phrase("Giữ skin đang chia sẻ") : Legacy.Tr.phrase("Chọn skin…")].concat(profileBridge.skinOptions.map(function(s) { return s.name; })); onActivated: function(i) { root.skinEntryId = i > 0 ? profileBridge.skinOptions[i - 1].entryId : ""; } }
    PaymentText { width: parent.width; text: Legacy.Tr.phrase("Chỉ ảnh skin được chia sẻ. Tài khoản Minecraft, đường dẫn máy và lịch sử chơi không được đưa lên hồ sơ."); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
    PaymentText { text: Legacy.Tr.phrase("Modpack hay chơi · Chọn tối đa 3"); font.weight: Font.DemiBold }
    Flow { width: parent.width; spacing: 8
        Repeater { model: root.favorites
            Button { label: modelData.title + "  ×"; selected: true; onClicked: root.togglePack(modelData) }
        }
    }
    Select { objectName: "profilePackChoice"; width: parent.width; model: [Legacy.Tr.phrase("Chọn từ bản chơi đã cài…")].concat(profileBridge.packOptions.map(function(p) { return p.title; })); enabled: root.favorites.length < 3; onActivated: function(i) { if (i > 0) root.togglePack(profileBridge.packOptions[i - 1]); currentIndex = 0; } }
    PaymentText { width: parent.width; text: Legacy.Tr.phrase("Bạn bè đã chấp nhận mới xem được hồ sơ. Chỉ những modpack bạn chọn mới xuất hiện."); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
}
