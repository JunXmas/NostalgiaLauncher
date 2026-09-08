import QtQuick
import QtQuick.Effects

/*
  Tấm kính mờ: lấy đúng vùng ảnh nằm sau nó, làm nhoè, rồi phủ một lớp tối trong suốt.

  Chỉ dùng cho những thứ nổi TRÊN ẢNH hero. Ở chỗ nền phẳng thì kính mờ và màn tối bán trong
  trông y như nhau, nên không đáng tốn một lượt vẽ thêm.

  Ảnh nền đứng yên, nên vùng phía sau chỉ chụp MỘT lần và chụp lại khi vùng đó đổi (kéo cửa
  sổ, thẻ nhích lúc rê chuột). `live: true` là chụp + làm mờ ở mỗi khung hình — với sáu thẻ
  cùng lúc là sáu lượt như thế 144 lần/giây, vô ích.
*/
Item {
    id: root
    // Ảnh phía sau, và vùng của nó (theo hệ toạ độ của chính ảnh) nằm ngay dưới tấm kính này.
    property Item backdrop: null
    property rect backdropRect: Qt.rect(0, 0, width, height)
    property color tint: "#8c14141a"
    property color borderColor: "#1affffff"
    property real radius: Theme.radiusSmall

    onBackdropRectChanged: capture.scheduleUpdate()
    Connections {
        // Ảnh nạp xong sau khi kính đã chụp lần đầu thì chụp lại, không thì kính trống.
        target: root.backdrop
        ignoreUnknownSignals: true
        function onStatusChanged() { capture.scheduleUpdate(); }
    }

    ShaderEffectSource {
        id: capture
        anchors.fill: parent
        visible: false
        sourceItem: root.backdrop
        sourceRect: root.backdropRect
        live: false
    }
    Rectangle {
        id: mask
        anchors.fill: parent
        radius: root.radius
        visible: false
        layer.enabled: true
    }
    MultiEffect {
        anchors.fill: parent
        source: capture
        visible: root.backdrop !== null
        blurEnabled: true
        blur: 1.0
        blurMax: 32
        autoPaddingEnabled: false
        maskEnabled: true
        maskSource: mask
    }
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: root.tint
        border.color: root.borderColor
        border.width: 1
    }
}
