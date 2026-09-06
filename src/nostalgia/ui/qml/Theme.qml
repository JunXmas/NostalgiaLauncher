pragma Singleton
import QtQuick

/*
  Bảng màu và nhịp chuyển động, gom một chỗ.

  Rải mã màu khắp các file QML là cách chắc chắn để một ngày có ba sắc xanh khác nhau cho
  cùng một ý nghĩa — đúng loại trôi dạt mà GLOSSARY.md chặn cho tên biến, nay chặn cho màu.
*/
QtObject {
    readonly property color background:  "#0a0d0b"
    readonly property color surface:     "#111713"
    readonly property color surfaceHigh: "#18201a"
    readonly property color border:      "#222c26"

    readonly property color accent:      "#4ade80"
    readonly property color accentDeep:  "#22a24f"
    readonly property color accentSoft:  "#1b3524"

    readonly property color text:        "#e9f1ec"
    readonly property color textMuted:   "#7f9488"
    readonly property color danger:      "#f2555a"

    readonly property int radius:        14
    readonly property int radiusSmall:   9
    readonly property int gap:           14
    readonly property int pad:           18

    // Một nhịp duy nhất cho mọi hoạt ảnh nhỏ. Mỗi chỗ một tốc độ khác nhau làm giao diện
    // trông rời rạc, dù từng chỗ nhìn riêng vẫn mượt.
    readonly property int quick:         120
    readonly property int normal:        220
    readonly property int slow:          420
}
