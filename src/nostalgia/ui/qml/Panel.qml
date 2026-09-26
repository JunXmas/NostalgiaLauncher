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

    /* Nét mực tối bao ngoài, 2 px.

       Đây là thứ làm giao diện đọc ra "hoạt hình" chứ không phải "phẳng tối": tranh vẽ tay
       bao mảng màu bằng nét, giao diện công cụ thì phân mảng bằng chênh lệch sắc độ. Viền
       trong hai tông ở dưới vẫn giữ — nó tạo khối; nét này tạo đường. Hai thứ khác việc.

       Tối hơn NỀN chứ không phải tối hơn mặt thẻ: nét phải bắt được cả khi thẻ nằm trên nền
       và khi thẻ nằm chồng lên thẻ khác. */
    border.width: 2
    border.color: Qt.darker(Theme.background, 1.7)

    // Chuyển sắc mặt + viền trong hai tông — cái làm thẻ nổi lên thành khối. Thẻ kính nằm
    // trên ảnh nền chỉ lấy viền: tô thêm chuyển sắc lên nền mờ là mất luôn vẻ trong.
    Bevel { faceOnly: root.translucent }

    // Tiêu đề: nhãn hoa bằng font pixel, trên một vạch xanh ngắn. Vạch làm mắt bắt được đầu
    // thẻ ngay cả khi liếc nhanh — chữ không thôi thì mọi thẻ nhìn như nhau.
    Row {
        id: heading
        visible: root.title.length > 0
        anchors { top: parent.top; left: parent.left; margins: Theme.pad }
        spacing: 9

        Rectangle {
            // 4 px, khớp vạch mục thanh bên: cùng một vai trò "đây là đầu một khối" thì phải
            // cùng một độ dày, nếu không hai chỗ nhìn như hai hệ thống khác nhau.
            width: 4; height: 14; color: Theme.accent
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
