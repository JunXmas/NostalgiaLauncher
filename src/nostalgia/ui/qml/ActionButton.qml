import QtQuick

/* Nút kiểu minecraft.net: vuông góc, viền tối 2 px, mặt xanh lá có vệt sáng ở mép trên và
   cạnh dưới tối dày như một khối; hover sáng lên, bấm thì lún xuống (cạnh dưới mỏng đi).
   `primary: false` cho nút phụ: cùng khối nhưng mặt xám đá. */
Item {
    id: root
    property string label: ""
    property bool primary: true
    // Nút nguy hiểm (DỪNG game): khối đỏ đất nung, cùng hình khối.
    property bool danger: false
    property bool clickable: true
    property int fontSize: 12
    signal clicked()

    readonly property int edge: 4         // cạnh dưới "khối"
    readonly property int pressDrop: press.pressed && root.clickable ? 3 : 0
    // Nút chính mang màu của tab đang mở (`Theme.accent`), không còn sắc lục viết cứng: nút
    // và tiêu đề trang nằm cùng một màn hình nên phải cùng một màu. Dịu đi một bậc so với
    // chữ tiêu đề — mặt nút là mảng màu lớn, để nguyên độ bão hoà thì chói.
    readonly property color baseFace: Qt.darker(Theme.accent, 1.35)
    readonly property color faceColor: !root.clickable ? "#5a5b5c"
                                      : root.danger ? (hover.hovered ? "#d4413c" : "#b8332f")
                                      : root.primary ? (hover.hovered ? Qt.lighter(baseFace, 1.22)
                                                                     : baseFace)
                                                     : (hover.hovered ? "#5a5c5e" : "#48494a")
    readonly property color edgeColor: !root.clickable ? "#3b3c3d"
                                      : root.danger ? "#5e1614"
                                      : root.primary ? Qt.darker(Theme.accent, 2.4) : "#2b2c2d"
    readonly property color glintColor: root.primary ? "#66ffffff" : "#33ffffff"

    height: 36
    implicitWidth: caption.width + 34

    // Viền tối bao cả khối.
    Rectangle { anchors.fill: parent; color: "#1e1e1f" }
    // Cạnh dưới tối.
    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 2 }
        height: parent.height - 4
        color: root.edgeColor
    }
    // Mặt nút, lún xuống khi bấm.
    Rectangle {
        id: face
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 2 }
        anchors.topMargin: 2 + root.pressDrop
        height: parent.height - 4 - root.edge + root.pressDrop
        color: root.faceColor
        Behavior on color { ColorAnimation { duration: Theme.quick } }
        Rectangle {
            anchors { left: parent.left; right: parent.right; top: parent.top }
            height: 2; color: root.glintColor
        }
        Text {
            id: caption
            anchors.centerIn: parent
            text: root.label
            color: !root.clickable ? "#b9b9b9" : "white"
            // Font pixel CHỈ cho nhãn viết hoa ("CHƠI ▶", "DỪNG ■"). Nhãn có chữ thường
            // ("Đăng nhập Microsoft") đặt vào F2D thì chật và khó đọc — chữ thường của font
            // pixel thấp, dấu tiếng Việt chồng lên làm dòng gồ ghề.
            font.family: root.label === root.label.toUpperCase() ? Theme.pixel : Theme.sans
            font.pixelSize: root.fontSize
            font.letterSpacing: Theme.trackLabel
            style: Text.Raised; styleColor: "#40000000"
        }
    }

    HoverHandler { id: hover; enabled: root.clickable; cursorShape: Qt.PointingHandCursor }
    TapHandler { id: press; enabled: root.clickable; onTapped: { notifier.playUi("select"); root.clicked(); } }
}
