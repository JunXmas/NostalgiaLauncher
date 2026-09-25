import QtQuick

/* Khung thẻ dùng chung cho mọi ô ở cột phải và ô danh sách bản chơi.

   Hình khối lấy theo công thức đo được trên chính CSS của minecraft.net: góc vuông tuyệt đối
   (`border-radius: 0` xuất hiện 57 lần, không có giá trị bo nào khác), và độ nổi làm bằng
   viền trong hai tông chứ không bằng đổ bóng —

       inset 2px 2px 0 0 rgba(255,255,255,.6), inset -2px -2px 0 0 rgba(255,255,255,.4)

   Dịch sang QML là bốn Rectangle 1px: sáng ở trên/trái, tối ở dưới/phải. Rẻ hơn đổ bóng
   nhiều lần, và là thứ duy nhất chạy được ở đây — máy không có GL phần cứng nên mọi hiệu ứng
   cần shader đều vẽ ra ảnh trắng (xem MicaBackdrop.qml).

   Mặt thẻ dùng chuyển sắc nhẹ thay cho một màu phẳng: đó là phần "mica" làm điểm nhấn.
   Không dùng quầng tròn — Rectangle bo góc cho mép cứng, nhìn ra ngay là hình tròn nằm dưới
   chứ không ra ánh sáng. */
Rectangle {
    id: root
    default property alias content: holder.data
    property string title: ""
    // Nằm trên ảnh nền thì để lộ ảnh phía sau một chút, như tấm kính.
    property bool translucent: false
    // Mép trên của vùng nội dung (dưới tiêu đề), để thẻ nào cao theo nội dung tính được chiều cao.
    readonly property alias contentTop: holder.y

    color: translucent ? "#d90f1512" : Theme.surface

    // Chuyển sắc mặt thẻ: sáng dần lên phía trên, như ánh sáng rọi từ trên xuống một khối đặc.
    Rectangle {
        anchors.fill: parent
        visible: !root.translucent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#14ffffff" }
            GradientStop { position: 0.55; color: "#00ffffff" }
            GradientStop { position: 1.0; color: "#14000000" }
        }
    }

    // Viền trong hai tông — cái làm thẻ nổi lên thành khối.
    Rectangle {
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: 1
        color: "#26ffffff"
    }
    Rectangle {
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        width: 1
        color: "#18ffffff"
    }
    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 1
        color: "#40000000"
    }
    Rectangle {
        anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
        width: 1
        color: "#30000000"
    }

    // Tiêu đề: nhãn hoa bằng font pixel, trên một vạch xanh ngắn. Vạch làm mắt bắt được đầu
    // thẻ ngay cả khi liếc nhanh — chữ không thôi thì mọi thẻ nhìn như nhau.
    Row {
        id: heading
        visible: root.title.length > 0
        anchors { top: parent.top; left: parent.left; margins: Theme.pad }
        spacing: 9

        Rectangle {
            width: 3; height: 13; color: Theme.accent
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: root.title
            color: Theme.accent
            font.family: Theme.pixel
            font.pixelSize: Theme.fontHeading
            font.letterSpacing: Theme.trackLabel
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    Item {
        id: holder
        anchors {
            top: heading.visible ? heading.bottom : parent.top
            topMargin: heading.visible ? 16 : Theme.pad
            left: parent.left; right: parent.right; bottom: parent.bottom
            leftMargin: Theme.pad; rightMargin: Theme.pad; bottomMargin: Theme.pad
        }
    }
}
