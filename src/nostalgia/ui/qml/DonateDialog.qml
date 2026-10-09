import QtQuick
import "preview" as Preview

/*
  Hộp ủng hộ: mã VietQR quét bằng app ngân hàng. Chỉ một đường duy nhất.

  KHÔNG nhúng số tiền vào mã — người ủng hộ tự gõ trong app ngân hàng của họ. Hiện tên chủ
  tài khoản và nội dung chuyển khoản ngay cạnh mã: người quét đối chiếu được trước khi bấm
  gửi, thay vì phải tin một ô vuông đen trắng mà mắt không đọc được.

  Chưa khai số tài khoản (`donateQr` rỗng) thì phần QR biến mất hẳn — hiện một khung trống
  là hứa một thứ không có.
*/
Item {
    id: dialog
    objectName: "donateDialog"
    visible: false
    z: 200

    function open() {
        dialog.visible = true;
        box.forceActiveFocus();
        notifier.playUi("open");
    }
    function dismiss() {
        dialog.visible = false;
        notifier.playUi("back");
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.AllButtons
        onWheel: function (wheel) { wheel.accepted = true; }
        Rectangle { anchors.fill: parent; color: "#b3000000" }
    }
    DialogFrame {
        id: box
        objectName: "donateFrame"
        anchors.centerIn: parent
        width: Math.min(620, parent.width - 48)
        height: Math.min(contentColumn.height + closeButton.height + 66, parent.height - 48)
        radius: Theme.radius; color: Theme.modern ? Qt.rgba(Theme.surface.r, Theme.surface.g, Theme.surface.b, 0.60) : Theme.surface; border.color: Theme.border
        focus: true
        Keys.onEscapePressed: dialog.dismiss()
        MouseArea { anchors.fill: parent; hoverEnabled: true }

        Preview.InertialScroll {
            id: donateScroll
            objectName: "donateScroll"
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 26; bottom: closeButton.top; bottomMargin: 14 }
            contentHeight: contentColumn.height
            Column {
                id: contentColumn
                width: donateScroll.width - 10
                spacing: 14
                Text {
                    width: parent.width; wrapMode: Text.WordWrap
                    text: Tr.phrase("Ủng hộ Nostalgia")
                    color: Theme.text; font.pixelSize: Theme.fontTitle; font.bold: true
                }
                Text {
                    width: parent.width; wrapMode: Text.WordWrap; lineHeight: 1.3
                    text: Tr.phrase("Launcher miễn phí và không quảng cáo. Ủng hộ là tuỳ tâm — bạn tự điền số tiền trong app ngân hàng.")
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody
                }
                Grid {
                    objectName: "donateTransferDetails"
                    width: parent.width
                    visible: settingsBridge.donateQr !== ""
                    columns: width >= 196 + 16 + 220 * Theme.textScale ? 2 : 1
                    spacing: 16
                    Rectangle {
                        // Nền trắng viền trắng quanh mã: máy quét cần vùng lặng (quiet zone) và
                        // cần tương phản. Đặt mã sẫm lên nền tối của Aero là mã không quét được.
                        // PNG đã tự mang viền trắng 4 ô, nên khung này chỉ cần bằng đúng ảnh.
                        objectName: "donateQrFrame"
                        width: 196; height: 196; radius: 6; color: "white"
                        Image {
                            objectName: "donateQrImage"
                            anchors.centerIn: parent
                            // KHÔNG đặt width/height: để ảnh vẽ 1:1 đúng số pixel nó có. Ép cỡ
                            // khác là ô vuông rơi vào ranh giới pixel lẻ và mã nhoè đi.
                            source: settingsBridge.donateQr
                            smooth: false  // mã QR là ô vuông sắc cạnh; làm mượt là làm nhoè
                        }
                    }
                    Column {
                        spacing: 8
                        width: parent.columns === 2 ? parent.width - 212 : parent.width
                        Text {
                            width: parent.width; wrapMode: Text.WordWrap
                            text: Tr.phrase("Quét bằng app ngân hàng")
                            color: Theme.text; font.pixelSize: Theme.fontBody; font.bold: true
                        }
                        Text {
                            objectName: "donateHolderText"
                            visible: text.length > 0
                            width: parent.width; wrapMode: Text.WordWrap
                            text: settingsBridge.donateAccountHolder
                            color: Theme.text; font.pixelSize: Theme.fontBody
                        }
                        Text {
                            objectName: "donateBankText"
                            visible: text.length > 0
                            width: parent.width; wrapMode: Text.WordWrap
                            text: settingsBridge.donateBankName
                            color: Theme.textMuted; font.pixelSize: Theme.fontBody
                        }
                        Text {
                            objectName: "donateMemoText"
                            width: parent.width; wrapMode: Text.WordWrap; lineHeight: 1.3
                            text: Tr.phrase("Nội dung: ") + settingsBridge.donateMemo
                            color: Theme.textMuted; font.pixelSize: Theme.fontBody
                        }
                    }
                }
            }
        }
        ActionButton {
            id: closeButton
            objectName: "donateClose"
            anchors { right: parent.right; bottom: parent.bottom; margins: 26 }
            label: Tr.phrase("Đóng")
            onClicked: dialog.dismiss()
        }
    }
}
