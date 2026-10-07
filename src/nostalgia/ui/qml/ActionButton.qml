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
    property int fontSize: Theme.fontBody
    signal clicked()
    activeFocusOnTab: root.clickable
    Accessible.role: Accessible.Button
    Accessible.name: root.label
    Accessible.onPressAction: root.trigger()
    Keys.onReturnPressed: root.trigger()
    Keys.onEnterPressed: root.trigger()
    Keys.onSpacePressed: function(event) { if (!event.isAutoRepeat) root.trigger(); }
    function trigger() {
        if (root.clickable) { notifier.playUi("select"); root.clicked(); }
    }
    Rectangle {
        objectName: "legacyButtonFocus"
        anchors.fill: parent; anchors.margins: -3
        color: "transparent"; border.width: 2; border.color: Theme.text
        visible: root.activeFocus && !Theme.modern; z: 2
    }

    readonly property int edge: 4         // cạnh dưới "khối"
    readonly property int pressDrop: press.pressed && root.clickable ? 3 : 0
    // Nút chính mang màu của tab đang mở (`Theme.accent`), không còn sắc lục viết cứng: nút
    // và tiêu đề trang nằm cùng một màn hình nên phải cùng một màu. Dịu đi một bậc so với
    // chữ tiêu đề — mặt nút là mảng màu lớn, để nguyên độ bão hoà thì chói.
    readonly property color baseFace: Qt.darker(Theme.accent, 2.0)
    readonly property color faceColor: !root.clickable ? "#5a5b5c"
                                      : root.danger ? (hover.hovered ? "#d4413c" : "#b8332f")
                                      : root.primary ? (hover.hovered ? Qt.lighter(baseFace, 1.08)
                                                                     : baseFace)
                                                     : (hover.hovered ? "#5a5c5e" : "#48494a")
    readonly property color edgeColor: !root.clickable ? "#3b3c3d"
                                      : root.danger ? "#5e1614"
                                      : root.primary ? Qt.darker(Theme.accent, 2.4) : "#2b2c2d"
    readonly property color glintColor: root.primary ? "#66ffffff" : "#33ffffff"

    height: Math.max(36, root.fontSize + 22)
    implicitWidth: caption.width + 34

    Item {
        anchors.fill: parent
        visible: !Theme.modern
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
            font.letterSpacing: root.label === root.label.toUpperCase() ? Theme.trackLabel : 0
            style: Text.Raised; styleColor: "#40000000"
        }
    }

    }
    Rectangle {
        objectName: "modernButtonFace"
        anchors.fill: parent
        visible: Theme.modern
        radius: 12
        color: root.danger ? Theme.mix(Theme.surface, Theme.danger, hover.hovered ? 0.4 : 0.28) : root.primary ? root.faceColor : hover.hovered ? Theme.surfaceHigh : Theme.surface
        border.color: root.activeFocus ? Theme.accent : root.danger ? Theme.danger : Theme.border
        border.width: root.activeFocus ? 2 : 1
        opacity: root.clickable ? 1 : 0.4
        scale: press.pressed ? 0.97 : 1
        Behavior on scale { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }
        Behavior on color { ColorAnimation { duration: Theme.quick } }
        Text {
            anchors.centerIn: parent
            text: root.label
            color: Theme.text
            font.family: Theme.sans
            font.pixelSize: root.fontSize
            font.weight: Font.DemiBold
        }
    }

    HoverHandler { id: hover; enabled: root.clickable; cursorShape: Qt.PointingHandCursor }
    TapHandler { id: press; enabled: root.clickable; onTapped: { root.forceActiveFocus(); root.trigger(); } }
}
