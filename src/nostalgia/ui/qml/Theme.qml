pragma Singleton
import QtQuick

/*
  Bảng màu và nhịp chuyển động, gom một chỗ.

  Rải mã màu khắp các file QML là cách chắc chắn để một ngày có ba sắc xanh khác nhau cho
  cùng một ý nghĩa — đúng loại trôi dạt mà GLOSSARY.md chặn cho tên biến, nay chặn cho màu.
*/
QtObject {
    // Nền: gần đen, hơi ngả xanh lá để ăn với màu nhấn.
    readonly property color background:  "#0b0f0c"
    readonly property color surface:     "#121814"
    readonly property color surfaceHigh: "#1a231d"
    readonly property color border:      "#243029"

    // Nhấn: xanh lá của khối cỏ Minecraft, đủ tương phản trên nền tối.
    readonly property color accent:      "#3ddc6b"
    readonly property color accentDeep:  "#2bb457"

    readonly property color text:        "#e8f0ea"
    readonly property color textMuted:   "#8ba192"
    readonly property color danger:      "#f2555a"

    readonly property int radius:        12
    readonly property int radiusSmall:   8
    readonly property int gap:           16

    // Một nhịp duy nhất cho mọi hoạt ảnh nhỏ. Mỗi chỗ một tốc độ khác nhau làm giao diện
    // trông rời rạc, dù từng chỗ nhìn riêng vẫn mượt.
    readonly property int quick:         120
    readonly property int normal:        220
    readonly property int slow:          420
}
