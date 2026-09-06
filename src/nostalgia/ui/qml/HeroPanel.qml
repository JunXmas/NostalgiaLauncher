import QtQuick

/*
  Khu ảnh lớn ở đầu trang chủ. Sáu thẻ nổi, mỗi thẻ đứng trên đúng một công trình trong ảnh
  (xem assets/README.md về ảnh). Ảnh đứng yên để thẻ và công trình không bao giờ lệch nhau;
  chuyển động nằm ở chấm neo và ở thẻ khi trỏ vào.
*/
Item {
    id: root
    property int instanceCount: 0
    signal navigate(int pageIndex)

    clip: true

    Image {
        id: photo
        anchors.fill: parent
        source: "assets/hero.jpg"
        fillMode: Image.PreserveAspectCrop
    }

    // Làm tối nhẹ ở đáy để nút CHƠI và dải chọn bản chơi nổi rõ trên nền lát đá.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.00; color: "#00000000" }
            GradientStop { position: 0.60; color: "#26000000" }
            GradientStop { position: 1.00; color: "#a6080c09" }
        }
    }

    // Toạ độ công trình đo trên ảnh gốc, tính theo phần trăm.
    HeroCard {
        objectName: "heroCard"
        landmarkX: 0.427; landmarkY: 0.31; pivot: 0.7    // ngôi nhà lớn giữa làng
        pageIndex: 1; glyph: "⛏"; title: "BẢN CHƠI"; subtitle: root.instanceCount + " đã tạo"
        backdrop: photo; onActivated: root.navigate(pageIndex)
    }
    HeroCard {
        objectName: "heroCard"
        landmarkX: 0.269; landmarkY: 0.475; below: true  // bàn chế tác bên trái
        pageIndex: 2; glyph: "⚙"; title: "MOD"; subtitle: "Duyệt & cài"
        backdrop: photo; onActivated: root.navigate(pageIndex)
    }
    HeroCard {
        objectName: "heroCard"
        landmarkX: 0.571; landmarkY: 0.215; pivot: 0.3   // tháp treo cờ
        pageIndex: 3; glyph: "☷"; title: "MÁY CHỦ"; subtitle: "Danh sách của bạn"
        backdrop: photo; onActivated: root.navigate(pageIndex)
    }
    HeroCard {
        objectName: "heroCard"
        landmarkX: 0.696; landmarkY: 0.32; below: true   // cổng xanh ngọc bên phải
        pageIndex: 4; glyph: "▤"; title: "TÀI NGUYÊN"; subtitle: "Gói & shader"
        backdrop: photo; onActivated: root.navigate(pageIndex)
    }
    HeroCard {
        objectName: "heroCard"
        landmarkX: 0.293; landmarkY: 0.29; below: true   // cổng Nether tím bên trái
        pageIndex: 5; glyph: "⛶"; title: "CHƠI CHUNG"; subtitle: "Chơi cùng bạn bè"
        backdrop: photo; onActivated: root.navigate(pageIndex)
    }
    HeroCard {
        objectName: "heroCard"
        landmarkX: 0.134; landmarkY: 0.255; pivot: 0.35  // ngôi nhà nhỏ bên trái
        pageIndex: 6; glyph: "☸"; title: "CÀI ĐẶT"; subtitle: "Tuỳ chọn launcher"
        backdrop: photo; onActivated: root.navigate(pageIndex)
    }
}
