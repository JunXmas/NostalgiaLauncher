import QtQuick

/* Trang chưa làm. Nói thẳng là chưa có, KHÔNG vẽ dữ liệu giả cho đẹp ảnh chụp. */
Item {
    Column {
        anchors.centerIn: parent
        spacing: 10
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Phần này chưa làm"
            color: Theme.text; font.pixelSize: 18; font.bold: true
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Sẽ có ở mốc sau. Ở đây không hiển thị số liệu giả."
            color: Theme.textMuted; font.pixelSize: 12
        }
    }
}
