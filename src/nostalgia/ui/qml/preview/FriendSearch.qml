import QtQuick
import "../" as Legacy

Item {
    id: root
    property alias text: query.text
    property string placeholder: Legacy.Tr.phrase("Tìm bạn theo tên…")
    height: query.height
    Keys.onEscapePressed: root.text = ""
    Input {
        id: query
        width: parent.width - (clear.visible ? clear.width + 8 : 0)
        placeholder: root.placeholder
        maximumLength: 128
    }
    Button {
        id: clear
        objectName: root.objectName + "Clear"
        anchors.right: parent.right
        width: 40 * GlassTheme.scale; height: query.height
        visible: !!root.text.length
        label: "×"; quiet: true
        Accessible.name: Legacy.Tr.phrase("Xóa tìm kiếm")
        onClicked: { root.text = ""; query.focusInput(); }
    }
}
