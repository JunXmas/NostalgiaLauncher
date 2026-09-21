import QtQuick

/*
  Thanh trượt kiểu Bedrock: rãnh vuông viền tối, phần đã qua sáng, phần còn lại tối, và núm
  là một khối vuông sáng CAO HƠN rãnh — nhô lên khỏi thanh đúng như ảnh mẫu, chứ không nằm
  lọt trong rãnh (lọt vào thì núm lẫn với phần sáng và không còn thấy mình đang kéo gì).

  API tối thiểu, đúng thứ ảnh mẫu cần: `value`, `from`, `to`, và `moved(real)` phát ra khi
  người dùng kéo hoặc bấm. Không có step/tick/nhãn vì chưa chỗ nào dùng.
*/
Item {
    id: root
    property real value: 0
    property real from: 0
    property real to: 100
    signal moved(real value)

    readonly property int knobWidth: 16
    readonly property int trackInset: 4                 // rãnh thấp hơn núm mỗi bên 4 px
    readonly property real span: root.to - root.from
    // Kẹp vào [0,1] để `value` ngoài khoảng không đẩy núm ra khỏi thanh.
    readonly property real fraction: root.span === 0
        ? 0 : Math.max(0, Math.min(1, (root.value - root.from) / root.span))
    readonly property real travel: Math.max(0, root.width - root.knobWidth)

    implicitWidth: 200; implicitHeight: 26
    width: implicitWidth; height: implicitHeight

    function valueAtX(pointX) {
        if (root.travel <= 0) return root.from;
        var offset = Math.max(0, Math.min(root.travel, pointX - root.knobWidth / 2));
        return root.from + (offset / root.travel) * root.span;
    }
    function moveTo(pointX) {
        var next = root.valueAtX(pointX);
        root.value = next;
        root.moved(next);
    }

    // ----- rãnh -----
    Rectangle {
        id: rail
        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter }
        height: parent.height - root.trackInset * 2
        color: Theme.blockBorder
        Rectangle {
            anchors.fill: parent; anchors.margins: 2
            color: Theme.blockTrack
            // Phần đã đi qua: sáng, kéo tới giữa núm.
            Rectangle {
                width: Math.max(0, knob.x + root.knobWidth / 2 - 2)
                height: parent.height
                color: Theme.blockLight
            }
        }
    }
    // ----- núm: khối cao hơn rãnh, có viền tối riêng -----
    Rectangle {
        id: knob
        x: root.fraction * root.travel
        width: root.knobWidth; height: parent.height
        color: Theme.blockBorder
        Rectangle {
            anchors.fill: parent; anchors.margins: 2
            color: hover.hovered || drag.active ? "#e8e9ea" : Theme.blockLight
            Behavior on color { ColorAnimation { duration: Theme.quick } }
            Rectangle {
                anchors { left: parent.left; right: parent.right; top: parent.top }
                height: 2; color: "#88ffffff"
            }
            Rectangle {
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                height: 2; color: "#55000000"
            }
        }
    }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    // Bấm vào rãnh nhảy tới chỗ đó; kéo thì bám theo con trỏ.
    TapHandler { onTapped: function (point) { root.moveTo(point.position.x); } }
    DragHandler {
        id: drag
        target: null
        xAxis.enabled: true; yAxis.enabled: false
        onCentroidChanged: if (drag.active) root.moveTo(drag.centroid.position.x)
    }
}
