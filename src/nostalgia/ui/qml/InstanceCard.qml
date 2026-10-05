import QtQuick

/* Thẻ một bản chơi: ô ảnh có nút chạy, rồi tên và thông tin thật bên dưới. */
Rectangle {
    id: root
    property string label: ""
    property string versionId: ""
    property bool playable: true
    property bool removable: false
    property bool editable: false
    property string iconUrl: ""
    property bool customGameDir: false
    // Thống kê chơi: chuỗi giờ chơi đã định dạng ở lõi, và ba con số đếm được.
    property string playtimeText: ""
    property int launchCount: 0
    property int worldCount: 0
    property int modCount: 0
    property bool confirmingRemove: false
    signal playRequested()
    signal removeRequested()
    signal editRequested()

    // Suy loader từ mã phiên bản: "fabric-loader-…", "1.20.1-forge-…", "neoforge-…".
    readonly property string loaderLabel: versionId.indexOf("fabric-loader-") === 0 ? "Fabric"
                                        : versionId.indexOf("quilt-loader-") === 0 ? "Quilt"
                                        : versionId.indexOf("neoforge") >= 0 ? "NeoForge"
                                        : versionId.indexOf("forge") >= 0 ? "Forge" : "Vanilla"

    implicitWidth: 230
    implicitHeight: 198
    radius: Theme.radius
    color: hover.hovered ? Theme.surfaceHigh : Theme.surface
    /* Nét mực tối 2 px, cùng công thức `Panel.qml` — không phải viền 1 px màu `border` như
       trước. Thẻ trước đây là mảng màu phẳng nằm bẹt giữa những thẻ Panel nổi lên quanh nó;
       lệch ấy đọc ra "thẻ này chưa làm xong", dù không ai chỉ ra được vì sao. */
    border.width: 2
    border.color: hover.hovered ? Theme.accent : Qt.darker(Theme.background, 1.7)
    opacity: 0
    scale: 0.97

    Behavior on color { ColorAnimation { duration: Theme.quick } }
    Behavior on border.color { ColorAnimation { duration: Theme.quick } }

    /* Trỏ vào thì thẻ NHẤC LÊN 3 px chứ chỉ đổi màu như trước.
       Dịch bằng `transform` chứ không bằng `y`: Grid và ListView là nơi đặt vị trí, gán `y`
       là phá bố cục của chúng. */
    transform: Translate {
        y: hover.hovered ? -3 : 0
        Behavior on y { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }
    }

    /* Cạnh dưới dày 5 px, như cạnh của `ActionButton`: bề dày là thứ nói "đây là khối đặc",
       chuyển sắc chỉ nói "có ánh sáng rọi vào". Cần cả hai mới ra chiều sâu.

       Pha 45% sắc tab vào chứ không tô xám suông: xám đặt cạnh nét mực (`darker(background,
       1.7)`) thì hai màu gần như trùng nhau và cạnh biến mất — chụp ảnh ra mới thấy, đọc mã
       hex thì không. */
    Rectangle {
        objectName: "cardEdge"
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 2 }
        height: 5
        color: Theme.mix(Theme.surface, Qt.darker(Theme.accent, hover.hovered ? 1.7 : 2.6), 0.45)
        Behavior on color { ColorAnimation { duration: Theme.quick } }
    }

    // Xuất hiện: mờ dần và phóng nhẹ. Không đụng x/y vì Grid mới là nơi đặt vị trí.
    Component.onCompleted: appear.start()
    ParallelAnimation {
        id: appear
        NumberAnimation { target: root; property: "opacity"; to: 1
                          duration: Theme.slow; easing.type: Easing.OutCubic }
        NumberAnimation { target: root; property: "scale"; to: 1.0
                          duration: Theme.slow; easing.type: Easing.OutCubic }
    }

    // Ô ảnh: chưa có ảnh riêng cho từng bản chơi nên dùng một mảng màu, không mượn ảnh giả.
    Rectangle {
        id: thumb
        anchors { top: parent.top; left: parent.left; right: parent.right; margins: 2 }
        height: 92
        radius: Theme.radius
        clip: true  // MicaBackdrop có lề âm: không clip là nền tràn ra ngoài thẻ, đè cả tiêu đề
        /* Pha từ `Theme.accent` chứ không phải hai mã lục viết cứng như trước: lục cố định
           nghĩa là ở sáu tab kia ô ảnh lệch tông với mọi thứ quanh nó. */
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.mix(Theme.surfaceHigh, Theme.accent, 0.22) }
            GradientStop { position: 1.0; color: Qt.darker(Theme.background, 1.25) }
        }

        /* Viền trong NGƯỢC chiều với thẻ: tối ở trên/trái, sáng ở dưới/phải. Đảo chiều ánh
           sáng là toàn bộ mẹo làm ô ảnh đọc ra một HỐC khoét vào mặt thẻ, trong khi thẻ đọc ra
           khối nhô lên. Cùng một nguồn sáng, hai hình trái dấu. */
        Rectangle {
            anchors { left: parent.left; right: parent.right; top: parent.top }
            height: 2; color: "#66000000"
        }
        Rectangle {
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
            width: 1; color: "#4d000000"
        }
        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: 1; color: "#1fffffff"
        }

        // Có icon (modpack) thì làm nền mica từ nó, và vẽ icon rõ ở giữa.
        MicaBackdrop { source: root.iconUrl; visible: root.iconUrl.length > 0 }
        ProjectIcon {
            visible: root.iconUrl.length > 0
            width: 48; height: 48
            anchors.centerIn: parent
            source: root.iconUrl
            fallbackText: root.label || "?"
        }

        // Vài khối mờ: đủ để ô ảnh trông có chủ ý, không phải một mảng trống vì lỗi.
        Row {
            visible: root.iconUrl.length === 0
            anchors { right: parent.right; bottom: parent.bottom; margins: 12 }
            spacing: 6
            Repeater {
                model: 3
                Rectangle {
                    width: 16; height: 16; radius: 0
                    color: Theme.accent
                    opacity: 0.10 + index * 0.05
                }
            }
        }

        Rectangle {
            anchors { left: parent.left; top: parent.top; margins: 10 }
            width: 30; height: 30; radius: 0
            color: playHover.hovered ? Theme.accent : "#b3000000"
            Behavior on color { ColorAnimation { duration: Theme.quick } }
            Text { anchors.centerIn: parent; text: "▶"; color: "white"; font.pixelSize: Theme.fontBody }
            HoverHandler { id: playHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { enabled: root.playable; onTapped: root.playRequested() }
        }
    }

    // Nút sửa (tên, RAM, cửa sổ), chỉ hiện khi trỏ vào.
    Text {
        anchors { right: parent.right; rightMargin: 48; top: thumb.bottom; topMargin: 14 }
        visible: root.editable
        opacity: hover.hovered ? 1 : 0
        text: "⚙"; font.pixelSize: Theme.fontHeading
        color: editHover.hovered ? Theme.accent : Theme.textMuted
        Behavior on opacity { NumberAnimation { duration: Theme.quick } }
        HoverHandler { id: editHover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: root.editRequested() }
    }

    // Gỡ hai bước: bấm thùng rác thì hiện "Gỡ?", bấm lần nữa mới gỡ thật. Rời chuột là huỷ.
    Rectangle {
        anchors { right: parent.right; top: thumb.bottom; margins: 10 }
        visible: root.removable
        opacity: hover.hovered ? 1 : 0
        width: removeText.width + 16; height: 24; radius: 0
        color: root.confirmingRemove ? Theme.danger : "transparent"
        Behavior on opacity { NumberAnimation { duration: Theme.quick } }
        Text {
            id: removeText
            anchors.centerIn: parent
            text: root.confirmingRemove ? "Gỡ?" : "🗑"
            font.pixelSize: Theme.fontBody; font.bold: root.confirmingRemove
            color: root.confirmingRemove ? "white" : (trashHover.hovered ? Theme.danger : Theme.textMuted)
        }
        HoverHandler { id: trashHover; cursorShape: Qt.PointingHandCursor }
        TapHandler {
            onTapped: {
                if (root.confirmingRemove) { root.confirmingRemove = false; root.removeRequested(); }
                else root.confirmingRemove = true;
            }
        }
    }

    Column {
        anchors { top: thumb.bottom; left: parent.left; right: parent.right; margins: 14 }
        spacing: 6
        Text {
            text: root.label; color: Theme.text; font.pixelSize: Theme.fontHeading; font.bold: true
            width: parent.width; elide: Text.ElideRight
        }
        Text {
            // 💾 đứng đầu: bản chơi này nằm ở thư mục riêng (ổ khác), không bị đuôi dài che mất.
            text: (root.customGameDir ? "💾  " : "") + root.loaderLabel + "  ·  " + root.versionId
            width: parent.width; elide: Text.ElideRight
            color: Theme.textMuted; font.pixelSize: Theme.fontBody
        }
        Text {
            objectName: "instanceStats"
            visible: root.playtimeText.length > 0
            // Ngắn để vừa thẻ 230 px: ⏱ giờ chơi · ▶ số lần chạy · 🌍 thế giới · ⚙ mod.
            text: "⏱ " + root.playtimeText
                  + (root.launchCount > 0 ? "  ·  ▶ " + root.launchCount : "")
                  + "  ·  🌍 " + root.worldCount + "  ·  ⚙ " + root.modCount
            width: parent.width; elide: Text.ElideRight
            color: root.launchCount > 0 ? Theme.accent : Theme.textMuted; font.pixelSize: Theme.fontLabel
        }
    }

    // Cuối file: viền trong phải nằm TRÊN ô ảnh, không thì ô ảnh đè mất mép sáng ở đỉnh thẻ.
    Bevel {}

    HoverHandler { id: hover; onHoveredChanged: if (!hovered) root.confirmingRemove = false }
}
