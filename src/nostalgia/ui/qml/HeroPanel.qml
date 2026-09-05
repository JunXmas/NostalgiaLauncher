import QtQuick

/*
  Khu ảnh lớn ở đầu trang chủ, kèm các thẻ nổi bấm được.

  Ảnh nền là ảnh chụp trong game **của chính chủ dự án** (xem assets/README.md). Nó dịch rất
  chậm theo kiểu Ken Burns: khung hình không bao giờ đứng chết, nhưng cũng không giật mắt khi
  người dùng đang đọc chữ đè lên nó.
*/
Item {
    id: root
    property int instanceCount: 0
    property int versionCount: 0
    property bool gameRunning: false
    signal navigate(int pageIndex)

    clip: true

    Image {
        id: photo
        anchors.fill: parent
        source: "assets/hero.jpg"
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        // Trôi rất chậm sang ngang rồi quay lại: đủ để thấy là sống, không đủ để gây khó chịu.
        scale: 1.06
        SequentialAnimation on x {
            loops: Animation.Infinite
            NumberAnimation { to: -18; duration: 22000; easing.type: Easing.InOutSine }
            NumberAnimation { to: 0; duration: 22000; easing.type: Easing.InOutSine }
        }
    }

    // Ảnh do người chơi chụp nên không đoán được chỗ nào sáng tối; phủ một lớp tối vừa đủ để
    // mọi chữ đè lên đều đọc được, và đậm dần xuống đáy cho liền với nền trang.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.00; color: "#3d000000" }
            GradientStop { position: 0.45; color: "#73080c09" }
            GradientStop { position: 1.00; color: Theme.background }
        }
    }

    // Thẻ trạng thái: chỉ nói những con số CÓ THẬT.
    Rectangle {
        anchors { top: parent.top; right: parent.right; margins: 18 }
        width: statusRow.width + 28
        height: 44
        radius: Theme.radiusSmall
        color: "#d9121a16"
        border.color: "#4d3a4a40"
        border.width: 1

        Row {
            id: statusRow
            anchors.centerIn: parent
            spacing: 18

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.instanceCount + " bản chơi"
                color: Theme.text; font.pixelSize: 12
            }
            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 7
                Rectangle {
                    width: 8; height: 8; radius: 4
                    anchors.verticalCenter: parent.verticalCenter
                    color: root.gameRunning ? Theme.accent : Theme.textMuted
                    SequentialAnimation on opacity {
                        running: root.gameRunning
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.35; duration: 900 }
                        NumberAnimation { to: 1.0; duration: 900 }
                    }
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.gameRunning ? "Đang chơi" : "Sẵn sàng"
                    color: Theme.textMuted; font.pixelSize: 12
                }
            }
        }
    }

    // Các thẻ nổi, rải như bản mẫu. STORE của bản mẫu đã thành CHƠI CHUNG.
    HeroCard {
        x: parent.width * 0.06; y: parent.height * 0.30
        objectName: "heroCard"
        glyph: "⛏"; title: "BẢN CHƠI"
        subtitle: root.instanceCount + " đã tạo"
        pageIndex: 1
        onActivated: root.navigate(pageIndex)
    }
    HeroCard {
        x: parent.width * 0.30; y: parent.height * 0.16
        objectName: "heroCard"
        pageIndex: 2
        glyph: "⚙"; title: "MOD"; subtitle: "Duyệt & cài"
        onActivated: root.navigate(pageIndex)
    }
    HeroCard {
        x: parent.width * 0.545; y: parent.height * 0.27
        objectName: "heroCard"
        pageIndex: 3
        glyph: "☷"; title: "MÁY CHỦ"; subtitle: "Danh sách của bạn"
        onActivated: root.navigate(pageIndex)
    }
    HeroCard {
        x: parent.width * 0.775; y: parent.height * 0.155
        objectName: "heroCard"
        pageIndex: 4
        glyph: "▤"; title: "TÀI NGUYÊN"; subtitle: "Gói & shader"
        onActivated: root.navigate(pageIndex)
    }
    HeroCard {
        x: parent.width * 0.315; y: parent.height * 0.545
        objectName: "heroCard"
        pageIndex: 5
        glyph: "⛶"; title: "CHƠI CHUNG"; subtitle: "Chơi cùng bạn bè"
        onActivated: root.navigate(pageIndex)
    }
    HeroCard {
        x: parent.width * 0.60; y: parent.height * 0.60
        objectName: "heroCard"
        pageIndex: 6
        glyph: "☸"; title: "CÀI ĐẶT"; subtitle: "Tuỳ chọn launcher"
        onActivated: root.navigate(pageIndex)
    }
}
