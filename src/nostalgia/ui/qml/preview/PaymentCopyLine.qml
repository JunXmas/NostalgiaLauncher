import QtQuick

Rectangle {
    id: root
    property string label: ""
    property string value: ""
    property string field: ""
    width: parent.width
    height: Math.max(50, labels.implicitHeight + 16)
    radius: 12
    color: GlassTheme.alpha(GlassTheme.background, 0.52)
    border.color: GlassTheme.stroke
    Column {
        id: labels
        anchors.left: parent.left
        anchors.leftMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width - (root.field ? copy.width + 34 : 28)
        spacing: 4
        PaymentText {
            width: parent.width
            text: root.label
            color: GlassTheme.muted
            font.pixelSize: 10 * GlassTheme.scale
        }
        PaymentText {
            objectName: "paymentField-" + root.field
            width: parent.width
            text: root.value
            font.weight: Font.DemiBold
        }
    }
    Button {
        id: copy
        objectName: "paymentCopy-" + root.field
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        visible: !!root.field
        label: copied ? "Đã chép" : "Chép"
        property bool copied: false
        quiet: true
        Accessible.name: "Sao chép " + root.label
        onClicked: {
            paymentBridge.copyField(root.field);
            copied = true;
            feedback.restart();
        }
        Timer {
            id: feedback
            interval: 1600
            onTriggered: copy.copied = false
        }
    }
}
