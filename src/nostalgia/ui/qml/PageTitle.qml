import QtQuick

/* Tiêu đề trang, dùng chung cho cả 6 tab.

   Trước khi có file này mỗi trang tự viết một `Text`: cỡ 22, 24, 18 — cùng một vai trò mà ba
   cỡ khác nhau, và đó chính là thứ làm các tab nhìn không giống nhau. Nay đổi kiểu ở đây là
   đổi cả sáu.

   Viết hoa và font pixel để khớp thanh bên: tên mục bên trái và tên trang bên phải là cùng
   một cấp bậc, phải cùng một kiểu chữ. F2D không có nét đậm nên KHÔNG đặt `font.bold` —
   Qt sẽ tự bôi đậm giả, chữ pixel bị nhoè. */
Text {
    property string caption: ""
    // `toUpperCase()` ở đây chứ không viết hoa sẵn ở chỗ gọi: cùng chuỗi `title` đó còn dùng
    // cho tiêu đề hộp thoại và câu hỏi xác nhận, nơi chữ thường mới đúng.
    text: caption.toUpperCase()
    color: Theme.text
    font.family: Theme.pixel
    font.pixelSize: Theme.fontTitle
    font.letterSpacing: Theme.trackLabel
}
