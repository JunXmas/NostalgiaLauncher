import QtQuick

/*
  Lớp thẻ nổi trên ảnh nền trang chủ. Sáu thẻ, mỗi thẻ đứng trên đúng một công trình.

  Ảnh nền do trang chủ vẽ (phủ kiểu cover, `PreserveAspectCrop`), còn lớp này phải có CÙNG kích
  thước với ảnh để ánh xạ toạ độ: phần trăm trên ảnh gốc -> pixel trên màn hình, có tính phần
  ảnh bị xén hai bên hoặc trên dưới.
*/
Item {
    id: root
    property int instanceCount: 0
    property Item photo: null
    // Tỉ lệ ảnh gốc (1800×1200). Đổi ảnh là đổi số này và đo lại toạ độ.
    readonly property real imageAspect: 1.5
    signal navigate(int pageIndex)
    signal navigateToLibrary(string contentKind)

    // Kích thước ảnh sau khi phủ cover, và phần bị xén (âm) ở mép trái / mép trên.
    readonly property real shownWidth: width / height >= imageAspect ? width : height * imageAspect
    readonly property real shownHeight: width / height >= imageAspect ? width / imageAspect : height
    readonly property real offsetX: (width - shownWidth) / 2
    readonly property real offsetY: (height - shownHeight) / 2

    function toPixelX(fraction) { return offsetX + fraction * shownWidth; }
    function toPixelY(fraction) { return offsetY + fraction * shownHeight; }

    // Toạ độ công trình đo trên ảnh gốc 2528×1686, tính theo phần trăm.
    HeroCard {
        objectName: "heroCard"
        landmarkX: 0.248; landmarkY: 0.506; pivot: 0.6     // Trái Đất khối, bên trái dưới
        pageIndex: 1; glyph: "⛏"; title: "BẢN CHƠI"; subtitle: root.instanceCount + " đã tạo"
        backdrop: root.photo; onActivated: root.navigate(pageIndex)
    }
    HeroCard {
        objectName: "heroCard"
        landmarkX: 0.515; landmarkY: 0.42; pivot: 0.85    // khối gỗ (Sao Mộc) chính giữa
        pageIndex: 2; glyph: "⚙"; title: "MOD"; subtitle: "Duyệt & cài"
        backdrop: root.photo; onActivated: root.navigate(pageIndex)
    }
    HeroCard {
        objectName: "heroCard"
        landmarkX: 0.672; landmarkY: 0.238; pivot: 1.0     // hành tinh vành xanh lục, trên phải (thẻ xoè trái, tránh cột HỒ SƠ)
        pageIndex: 3; glyph: "☺"; title: "TÀI KHOẢN"; subtitle: "Skin, cape, đăng nhập"
        backdrop: root.photo; onActivated: root.navigate(pageIndex)
    }
    HeroCard {
        objectName: "heroCard"
        landmarkX: 0.660; landmarkY: 0.522; below: true; pivot: 1.0 // hành tinh vành xanh lam, dưới phải (thẻ xoè trái)
        pageIndex: 2; glyph: "▤"; title: "TÀI NGUYÊN"; subtitle: "Gói & shader"
        backdrop: root.photo; onActivated: root.navigateToLibrary("resourcepack")
    }
    HeroCard {
        objectName: "heroCard"
        landmarkX: 0.325; landmarkY: 0.315; pivot: 0.35    // khối đỏ (Sao Hoả), thẻ xoè phải để không đụng thẻ Sao Thuỷ
        pageIndex: 4; glyph: "⛶"; title: "CHƠI CHUNG"; subtitle: "Chơi cùng bạn bè"
        backdrop: root.photo; onActivated: root.navigate(pageIndex)
    }
    HeroCard {
        objectName: "heroCard"
        landmarkX: 0.175; landmarkY: 0.255; below: true; pivot: 0.35 // khối xám (Sao Thuỷ), thẻ treo dưới để không đụng thẻ Sao Hoả
        pageIndex: 5; glyph: "☸"; title: "CÀI ĐẶT"; subtitle: "Tuỳ chọn launcher"
        backdrop: root.photo; onActivated: root.navigate(pageIndex)
    }
}
