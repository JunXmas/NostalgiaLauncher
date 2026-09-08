import QtQuick

/*
  Nhân vật vẽ từ skin 64x64 bằng cách cắt vùng UV, không cần OpenGL/three.js. Bốn hướng nhìn
  (trước, phải, sau, trái) chuyển bằng `facing`; `slim` = tay 3 pixel (Alex). Lớp ngoài (áo/mũ)
  vẽ đè lên lớp trong, nhô ra 1 pixel skin. `pixel` là số điểm màn hình cho một pixel skin.
*/
Item {
    id: root
    property string source: ""
    property bool slim: false
    property int facing: 0          // 0 trước, 1 phải, 2 sau, 3 trái
    property real pixel: 6
    readonly property int armWidth: slim ? 3 : 4
    width: pixel * 16; height: pixel * 32

    // Toạ độ UV (x, y, w, h) từng hộp theo hướng nhìn: [trước, phải, sau, trái].
    // Đầu 8x8x8 tại (0,0); thân 8x12x4 tại (16,16); tay 4x12x4 tại (40,16)/(32,48); chân (0,16)/(16,48).
    function box(originX, originY, w, h, depth, side) {
        // Hộp UV chuẩn của Minecraft: [trái|trước|phải|sau] xếp ngang từ (originX, originY+depth).
        var faces = [
            Qt.rect(originX + depth, originY + depth, w, h),                 // trước
            Qt.rect(originX, originY + depth, depth, h),                     // trái của nhân vật = phải người nhìn? (xem dưới)
            Qt.rect(originX + depth + w + depth, originY + depth, w, h),     // sau
            Qt.rect(originX + depth + w, originY + depth, depth, h)          // phải
        ];
        // Nhìn từ phía "phải" (facing 1) thấy mặt phải của hộp; hoán đổi cho đúng chiều.
        var order = [0, 3, 2, 1];
        return faces[order[side]];
    }
    function partWidth(w, depth, side) { return (side === 0 || side === 2) ? w : depth; }

    // Một bộ phận: lớp trong + lớp ngoài (nếu có), đặt theo pixel.
    component Part: Item {
        property int ox: 0; property int oy: 0; property int w: 8; property int h: 8; property int depth: 8
        property int overlayX: -1; property int overlayY: -1
        property real px: 0; property real py: 0
        readonly property int shown: root.partWidth(w, depth, root.facing)
        x: px * root.pixel; y: py * root.pixel
        width: shown * root.pixel; height: h * root.pixel
        Image {
            anchors.fill: parent; cache: true
            source: root.source; smooth: false
            sourceClipRect: root.box(ox, oy, w, h, depth, root.facing)
        }
        Image {
            visible: overlayX >= 0; cache: true
            anchors.fill: parent; anchors.margins: -root.pixel * 0.5
            source: root.source; smooth: false
            sourceClipRect: root.box(overlayX, overlayY, w, h, depth, root.facing)
        }
    }

    // Vị trí theo hướng: bề ngang nhân vật thay đổi giữa nhìn trước (16) và nhìn nghiêng (8).
    readonly property bool sideways: facing === 1 || facing === 3
    readonly property real centerX: 8
    readonly property bool mirrored: facing === 2 || facing === 3

    Part { ox: 0; oy: 0; w: 8; h: 8; depth: 8; overlayX: 32; overlayY: 0
           px: root.centerX - 4; py: 0 }
    Part { ox: 16; oy: 16; w: 8; h: 12; depth: 4; overlayX: 16; overlayY: 32
           px: root.sideways ? root.centerX - 2 : root.centerX - 4; py: 8 }
    // Tay: nhìn trước thấy tay phải nhân vật bên trái màn hình. Nhìn nghiêng chỉ thấy một tay.
    Part { visible: !root.sideways || root.facing === 1
           ox: 40; oy: 16; w: root.armWidth; h: 12; depth: 4; overlayX: 40; overlayY: 32
           px: root.sideways ? root.centerX - 2 : (root.mirrored ? root.centerX + 4 : root.centerX - 4 - root.armWidth); py: 8 }
    Part { visible: !root.sideways || root.facing === 3
           ox: 32; oy: 48; w: root.armWidth; h: 12; depth: 4; overlayX: 48; overlayY: 48
           px: root.sideways ? root.centerX - 2 : (root.mirrored ? root.centerX - 4 - root.armWidth : root.centerX + 4); py: 8 }
    Part { ox: 0; oy: 16; w: 4; h: 12; depth: 4; overlayX: 0; overlayY: 32
           px: root.sideways ? root.centerX - 2 : (root.mirrored ? root.centerX : root.centerX - 4); py: 20 }
    Part { visible: !root.sideways
           ox: 16; oy: 48; w: 4; h: 12; depth: 4; overlayX: 0; overlayY: 48
           px: root.mirrored ? root.centerX - 4 : root.centerX; py: 20 }
}
