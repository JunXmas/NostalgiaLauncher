import QtQuick
import "../" as Legacy

/* Công tắc Nos Client đặt ngay chỗ người chơi bấm Chơi (thẻ bản chơi, khối CHƠI trang chủ).
   Trước đây chỉ có trong Quản lý → Tổng quan — người chơi không tìm thấy.
   Chỉ hiện ở bản chơi Nos hỗ trợ (Fabric 1.21.11); khoá khi game đang chạy. */
Rectangle {
    id: root
    property var entry: ({})
    // Thẻ hẹp (cột lưới) không đủ chỗ cho "Nos Client: Bật" cạnh nút Chơi → rút còn "Nos"; chấm màu vẫn báo bật/tắt.
    property real maxWidth: Infinity
    readonly property bool brief: fullLabel.width + 37 > maxWidth
    readonly property bool on: entry.nosClientEnabled === true
    readonly property bool locked: bridge.gameRunning || bridge.busy
    // Câu giải thích cho ActionHint bên cạnh (không có tooltip trong bộ giao diện này).
    readonly property string hint: locked ? Legacy.Tr.phrase("Đóng Minecraft để bật hoặc tắt Nos Client.") : on ? Legacy.Tr.phrase("Nos Client bật: HUD, minimap, waypoint, zoom. Trong game bấm R-Shift để mở cài đặt.") : Legacy.Tr.phrase("Bật Nos Client để có HUD, minimap, waypoint, zoom. Launcher tự tải bản mới nhất.")
    objectName: "nosChip-" + (entry.instanceId || "")
    visible: entry.nosClientSupported === true
    height: 30
    width: chipRow.implicitWidth + 22
    radius: height / 2
    color: on ? GlassTheme.alpha(GlassTheme.brand, hover.hovered ? 0.30 : 0.20) : hover.hovered ? GlassTheme.raised : GlassTheme.alpha(GlassTheme.raised, 0.6)
    border.color: activeFocus ? GlassTheme.accent : on ? GlassTheme.alpha(GlassTheme.brand, 0.75) : GlassTheme.stroke
    border.width: activeFocus ? 2 : 1
    // Bàn phím: Tab tới rồi Enter/Space để bật/tắt, như mọi nút khác.
    activeFocusOnTab: true
    Keys.onReturnPressed: flip()
    Keys.onEnterPressed: flip()
    Keys.onSpacePressed: flip()
    opacity: locked ? 0.55 : 1
    Behavior on color { ColorAnimation { duration: GlassTheme.quick } }
    Accessible.role: Accessible.CheckBox
    Accessible.name: Legacy.Tr.phrase("Nos Client")
    Accessible.checkable: true
    Accessible.checked: on
    Accessible.onToggleAction: root.flip()
    function flip() {
        if (!locked && entry.instanceId) bridge.toggleNosClient(entry.instanceId, !on);
    }
    Row {
        id: chipRow
        anchors.centerIn: parent
        spacing: 7
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: 8; height: 8; radius: 4
            color: root.on ? GlassTheme.brand : GlassTheme.muted
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.brief ? "Nos" : fullLabel.text
            color: root.on ? GlassTheme.text : GlassTheme.muted
            font.family: GlassTheme.font
            font.pixelSize: GlassTheme.fontLabel
            font.weight: Font.DemiBold
        }
    }
    TextMetrics {
        id: fullLabel
        text: root.on ? Legacy.Tr.phrase("Nos Client: Bật") : Legacy.Tr.phrase("Nos Client: Tắt")
        font.family: GlassTheme.font
        font.pixelSize: GlassTheme.fontLabel
        font.weight: Font.DemiBold
    }
    HoverHandler { id: hover; cursorShape: root.locked ? Qt.ArrowCursor : Qt.PointingHandCursor }
    TapHandler { onTapped: root.flip() }
}
