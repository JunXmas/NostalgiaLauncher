import QtQuick

/* Độ nổi của một khối, tách ra dùng chung.

   Công thức đo trên CSS của minecraft.net: không đổ bóng, mà là viền trong hai tông —

       inset 2px 2px 0 0 rgba(255,255,255,.6), inset -2px -2px 0 0 rgba(255,255,255,.4)

   cộng một chuyển sắc mặt (sáng trên, tối dưới) cho khối trông đặc chứ không phải mảng phẳng.
   Rẻ hơn đổ bóng nhiều lớp, và là thứ DUY NHẤT chạy được ở đây: máy không có GL phần cứng nên
   mọi hiệu ứng cần shader vẽ ra ảnh trắng (xem MicaBackdrop.qml).

   Panel và InstanceCard đều cần đúng thứ này. Chép hai bản thì một ngày hai chỗ lệch tông và
   thẻ trong lưới nhìn như thuộc một ứng dụng khác — đúng loại trôi dạt mà Theme.qml chặn cho
   màu, nay chặn cho hình khối. */
Item {
    id: root
    // Mặt phẳng tuyệt đối (thẻ kính trên ảnh nền): chỉ vẽ viền, không tô chuyển sắc.
    property bool faceOnly: false

    anchors.fill: parent

    Rectangle {
        anchors.fill: parent
        visible: !root.faceOnly
        gradient: Gradient {
            GradientStop { position: 0.0;  color: "#14ffffff" }
            GradientStop { position: 0.55; color: "#00ffffff" }
            GradientStop { position: 1.0;  color: "#14000000" }
        }
    }

    Rectangle {
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: 1; color: "#26ffffff"
    }
    Rectangle {
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        width: 1; color: "#18ffffff"
    }
    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 1; color: "#40000000"
    }
    Rectangle {
        anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
        width: 1; color: "#30000000"
    }
}
