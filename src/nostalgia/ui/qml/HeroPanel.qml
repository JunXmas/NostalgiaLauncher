import QtQuick

/*
  Khu ảnh lớn ở đầu trang chủ.

  Bản mẫu dùng một ảnh render Minecraft. Ở đây cố tình KHÔNG nhúng ảnh của Mojang: đó là nội
  dung có bản quyền của người khác. Thay vào đó là một khung cảnh dựng bằng hình khối — vẫn
  gợi đúng cảm giác, và là thứ của mình. Sau này chỗ này sẽ thay bằng ảnh chụp trong game
  của chính người chơi.
*/
Item {
    id: root
    property int instanceCount: 0
    property bool gameRunning: false

    clip: true

    // Trời hoàng hôn: tím sâu trên cao, ấm dần xuống đường chân trời. Cùng tinh thần với
    // bản mẫu, nhưng là hình của mình chứ không mượn ảnh có bản quyền.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.00; color: "#241a3f" }
            GradientStop { position: 0.42; color: "#5b3a63" }
            GradientStop { position: 0.68; color: "#a05a4a" }
            GradientStop { position: 0.80; color: "#3f3a34" }
            GradientStop { position: 1.00; color: "#131a15" }
        }
    }

    // Mặt trời lặn: một vệt sáng ấm ngay trên đường chân trời.
    Rectangle {
        width: parent.width * 0.5
        height: width
        radius: width / 2
        x: parent.width * 0.62
        y: parent.height * 0.34
        opacity: 0.22
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#ffd9a0" }
            GradientStop { position: 1.0; color: "#00000000" }
        }
    }

    // Vài "khối" trôi rất chậm, gợi thế giới khối vuông mà không cần ảnh.
    Repeater {
        model: 7
        Rectangle {
            width: 30 + (index % 3) * 16
            height: width
            radius: 5
            color: index % 2 === 0 ? "#6d8f5a" : "#7a6a92"
            opacity: 0.5
            x: root.width * (0.08 + index * 0.13)
            y: root.height * 0.2
            rotation: index * 9

            SequentialAnimation on y {
                loops: Animation.Infinite
                NumberAnimation { to: root.height * 0.34; duration: 4200 + index * 500
                                  easing.type: Easing.InOutSine }
                NumberAnimation { to: root.height * 0.18; duration: 4200 + index * 500
                                  easing.type: Easing.InOutSine }
            }
        }
    }

    // Chỉ phủ tối phần đáy, vừa đủ để chữ đọc được mà không giết cả bầu trời.
    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: parent.height * 0.55
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#00000000" }
            GradientStop { position: 0.6; color: "#b3080c09" }
            GradientStop { position: 1.0; color: Theme.background }
        }
    }

    // Thẻ trạng thái: chỉ nói những con số CÓ THẬT.
    Rectangle {
        anchors { top: parent.top; right: parent.right; margins: 18 }
        width: statusRow.width + 28
        height: 44
        radius: Theme.radiusSmall
        color: "#c0121814"
        border.color: Theme.border
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
}
