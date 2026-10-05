import QtQuick

/*
  Lớp thẻ chức năng neo vào các hành tinh trong ảnh hero — CHỈ hiện khi thanh bên thu gọn.

  Sáu thẻ = sáu mục còn lại của thanh bên (TRANG CHỦ là chính trang đang mở nên không cần
  thẻ). Toạ độ hành tinh đo trên ảnh gốc 2528×1686 theo phần trăm — thừa kế từ HeroPanel cũ
  (bỏ ở 1.0.14), đã đo lại tâm hai hành tinh có vành ở c720f66.

  Lớp này phải có CÙNG kích thước với ảnh nền để ánh xạ toạ độ: phần trăm trên ảnh gốc →
  pixel trên màn hình, có tính phần ảnh bị xén hai bên hoặc trên dưới (PreserveAspectCrop).
*/
Item {
    id: root
    // Bề rộng bị cột phải chiếm: thẻ nào cũng phải nằm gọn bên trái vùng này.
    property real reservedRight: 0
    readonly property real freeRight: width - reservedRight
    // Tỉ lệ ảnh gốc. Đổi ảnh là đổi số này và đo lại toạ độ.
    readonly property real imageAspect: 1.5
    signal navigate(int pageIndex)

    // Kích thước ảnh sau khi phủ cover, và phần bị xén (âm) ở mép trái / mép trên.
    readonly property real shownWidth: width / height >= imageAspect ? width : height * imageAspect
    readonly property real shownHeight: width / height >= imageAspect ? width / imageAspect : height
    readonly property real offsetX: (width - shownWidth) / 2
    readonly property real offsetY: (height - shownHeight) / 2

    function toPixelX(fraction) { return offsetX + fraction * shownWidth; }
    function toPixelY(fraction) { return offsetY + fraction * shownHeight; }

    PlanetCard {
        objectName: "planetCard"
        landmarkX: 0.248; landmarkY: 0.506; pivot: 0.6; entryIndex: 0   // Trái Đất khối, trái dưới
        pageIndex: 1; glyph: "⛏"; block: "crafting"
        title: Tr.text("instances"); subtitle: bridge.instances.length + " " + Tr.text("instance_count_suffix")
        onActivated: root.navigate(pageIndex)
    }
    PlanetCard {
        objectName: "planetCard"
        landmarkX: 0.515; landmarkY: 0.42; pivot: 0.85; entryIndex: 1   // khối gỗ (Sao Mộc) giữa
        pageIndex: 2; glyph: "⚙"; block: "bookshelf"
        title: Tr.text("library"); subtitle: Tr.text("planet_library_hint")
        onActivated: root.navigate(pageIndex)
    }
    PlanetCard {
        objectName: "planetCard"
        landmarkX: 0.672; landmarkY: 0.238; entryIndex: 2               // hành tinh vành lục, trên phải
        pageIndex: 3; glyph: "☺"; block: "diamond"
        title: Tr.text("accounts"); subtitle: Tr.text("planet_accounts_hint")
        onActivated: root.navigate(pageIndex)
    }
    PlanetCard {
        objectName: "planetCard"
        landmarkX: 0.325; landmarkY: 0.315; pivot: 0.35; entryIndex: 3  // khối đỏ (Sao Hoả)
        pageIndex: 4; glyph: "⛶"; block: "command"
        title: Tr.text("multiplayer"); subtitle: Tr.text("planet_multiplayer_hint")
        onActivated: root.navigate(pageIndex)
    }
    PlanetCard {
        objectName: "planetCard"
        landmarkX: 0.660; landmarkY: 0.522; below: true; entryIndex: 4  // hành tinh vành lam, dưới phải
        pageIndex: 5; glyph: "≡"; block: "chest"
        title: Tr.text("log"); subtitle: Tr.text("planet_log_hint")
        onActivated: root.navigate(pageIndex)
    }
    PlanetCard {
        objectName: "planetCard"
        landmarkX: 0.175; landmarkY: 0.255; below: true; pivot: 0.35; entryIndex: 5 // khối xám (Sao Thuỷ)
        pageIndex: 6; glyph: "☸"; block: "redstone"
        title: Tr.text("settings"); subtitle: Tr.text("planet_settings_hint")
        onActivated: root.navigate(pageIndex)
    }
}
