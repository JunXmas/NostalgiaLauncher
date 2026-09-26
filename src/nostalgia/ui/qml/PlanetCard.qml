import QtQuick

/*
  Thẻ chức năng neo vào MỘT HÀNH TINH trong ảnh hero — bản kế nhiệm của HeroCard (bỏ ở
  1.0.14 vì trùng đường đi với thanh bên). Nay nó chỉ hiện khi thanh bên THU GỌN, nên không
  còn hai đường cùng hình dạng: thu gọn là các nút "bay ra" từ hành tinh thay chỗ thanh bên.

  `landmarkX/Y` là toạ độ hành tinh theo phần trăm ảnh (đo trên ảnh gốc 2528×1686), nên đổi
  kích thước cửa sổ thì chấm neo vẫn đứng đúng hành tinh. `pivot` là vị trí ưu tiên của chấm
  neo trên bề ngang thẻ; thẻ bị đẩy vào vùng trống thì dịch, chấm neo đứng yên.

  Rê chuột: thẻ NHẤC LÊN và hành tinh GLOW — quầng sáng là ảnh PNG toả tròn (assets/glow.png,
  sinh bằng script trong repo) vì máy không có GL phần cứng thì shader vẽ ra ảnh trắng.
  Không có hoạt ảnh vô hạn: glow chỉ chuyển khi hover đổi, đứng yên tốn 0% CPU.
*/
Item {
    id: root
    property string title: ""
    property string subtitle: ""
    property string glyph: ""
    property string block: ""
    property real landmarkX: 0.5
    property real landmarkY: 0.5
    property real pivot: 0.5
    property bool below: false
    // Trang mà thẻ này dẫn tới, và cũng là màu của thẻ (cùng bảng với thanh bên).
    property int pageIndex: 0
    // Thứ tự xuất hiện: các thẻ bay ra lần lượt chứ không bật cùng lúc.
    property int entryIndex: 0
    // Test và preview bật glow không cần con chuột thật.
    property bool forceGlow: false
    signal activated()

    readonly property color tint: Theme.accents[Math.min(pageIndex, Theme.accents.length - 1)]
    readonly property bool lit: hover.hovered || forceGlow
    readonly property int cardHeight: 56
    readonly property int stemLength: 22
    readonly property real anchorX: parent.toPixelX(landmarkX)
    readonly property real anchorY: parent.toPixelY(landmarkY)

    width: row.width + 34
    height: cardHeight + stemLength
    x: Math.round(Math.max(0, Math.min(anchorX - width * pivot, parent.freeRight - width)))
    y: Math.round(anchorY - (below ? 0 : height))

    // Cho test bấm được thẻ mà không phải mô phỏng chuột qua offscreen.
    function trigger() { root.activated(); }

    // Bay ra từ hành tinh: phóng từ chấm neo + hiện dần, so le theo `entryIndex`.
    // Chạy MỘT lần mỗi lần hiện — không phải vòng lặp vô hạn.
    scale: 0
    opacity: 0
    transformOrigin: below ? Item.Top : Item.Bottom
    onVisibleChanged: if (visible) entrance.restart()
    Component.onCompleted: if (visible) entrance.restart()
    SequentialAnimation {
        id: entrance
        PauseAnimation { duration: 90 * root.entryIndex }
        ParallelAnimation {
            NumberAnimation { target: root; property: "scale"; from: 0.2; to: 1
                              duration: Theme.slow; easing.type: Easing.OutBack }
            NumberAnimation { target: root; property: "opacity"; from: 0; to: 1
                              duration: Theme.normal }
        }
    }

    // Quầng sáng của hành tinh, đặt DƯỚI thẻ và chấm neo. Tâm quầng = tâm chấm neo.
    Image {
        id: glow
        objectName: "planetGlow"
        source: "assets/glow.png"
        width: 230; height: 230
        x: Math.round(Math.min(Math.max(root.anchorX - root.x, 8), root.width - 8) - width / 2)
        y: Math.round((root.below ? 0 : root.height) - height / 2)
        opacity: root.lit ? 0.85 : 0
        scale: root.lit ? 1 : 0.55
        Behavior on opacity { NumberAnimation { duration: Theme.normal } }
        Behavior on scale { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
    }

    // Chấm neo trên hành tinh, mang màu của trang đích.
    Rectangle {
        id: pin
        width: 10; height: 10; radius: 5
        x: Math.round(Math.min(Math.max(root.anchorX - root.x, 8), root.width - 8) - 5)
        y: root.below ? -5 : root.height - 5
        color: root.tint
        border.color: "#a0ffffff"
        border.width: 2
        scale: root.lit ? 1.3 : 1
        Behavior on scale { NumberAnimation { duration: Theme.quick } }
    }
    Rectangle {
        width: 2
        height: root.stemLength - 4
        x: pin.x + 4
        y: root.below ? 4 : root.cardHeight
        color: "#b3ffffff"
    }

    Item {
        id: body
        width: parent.width
        height: root.cardHeight
        y: (root.below ? root.stemLength : 0) + (root.lit ? (root.below ? 3 : -3) : 0)
        scale: press.pressed ? 0.97 : (root.lit ? 1.04 : 1.0)
        Behavior on scale { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }
        Behavior on y { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }

        // Cùng công thức kính của Panel translucent: mặt mờ + nét mực + viền hai tông.
        Rectangle {
            anchors.fill: parent
            color: "#d90f1512"
            border.width: 2
            border.color: root.lit ? root.tint : Qt.darker(Theme.background, 1.7)
            Behavior on border.color { ColorAnimation { duration: Theme.quick } }
            Bevel { faceOnly: true }
        }

        Row {
            id: row
            anchors.centerIn: parent
            spacing: 12

            Rectangle {
                width: 30; height: 30; radius: 0
                anchors.verticalCenter: parent.verticalCenter
                color: root.lit ? root.tint : Qt.darker(root.tint, 1.55)
                Behavior on color { ColorAnimation { duration: Theme.quick } }
                BlockIcon {
                    anchors.centerIn: parent
                    width: 22; height: 22
                    block: root.block
                    glyph: root.glyph
                    glyphColor: "white"
                    spinning: root.lit
                }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Text {
                    text: root.title
                    color: Theme.text
                    font.family: Theme.pixel
                    font.pixelSize: Theme.fontHeading
                    font.letterSpacing: Theme.trackLabel
                }
                Text { text: root.subtitle; color: Theme.textMuted; font.pixelSize: Theme.fontLabel }
            }
        }

        HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
        TapHandler { id: press; onTapped: root.trigger() }
    }
}
