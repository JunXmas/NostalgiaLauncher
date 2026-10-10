import QtQuick
import "../" as Legacy

Item {
    Component.onCompleted: GlassTheme.preferences = settingsBridge
    implicitHeight: contents.implicitHeight
    height: implicitHeight
    Column {
        id: contents
        width: parent.width
        spacing: 10
        PaymentText {
            width: parent.width
            text: Legacy.Tr.phrase("Diện mạo launcher")
            font.pixelSize: GlassTheme.fontSubheading
            font.weight: Font.DemiBold
        }
        PaymentText {
            width: parent.width
            text: settingsBridge.interfaceStyle === "classic" ? Legacy.Tr.phrase("Đang sử dụng giao diện cũ.") : Legacy.Tr.phrase("Đang sử dụng giao diện mới.")
            color: GlassTheme.muted
        }
        Button {
            objectName: "interfaceChoiceChange"
            label: Legacy.Tr.phrase("Đổi giao diện…")
            clickable: !bridge.busy && !accountBridge.busy && !contentBridge.busy && !storageBridge.busy && !importBridge.busy
            onClicked: interfaceSetup.openChooser()
        }
    }
}
