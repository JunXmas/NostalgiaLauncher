import QtQuick

/*
  Một ô lọc chọn-nhiều thu gọn: đóng lại chỉ chiếm một ô, bấm mới bung khay để tick.

  Vì sao có: cột lọc cũ trải thẳng 4 loader + hàng chục phiên bản game thành hàng dọc, nên
  phần SORT bị đẩy khỏi tầm mắt và danh mục phiên bản phải cắt bớt cho vừa cột. Gói lại
  thành ô thì danh sách bên trong cuộn được, không phải cắt.

  Khay treo lên contentItem của cửa sổ, cùng lý do như `Dropdown`: nằm trong cây của ô thì
  thứ tự vẽ của cha quyết định, và các hàng đè lên thẻ kết quả bị thẻ hứng mất cú bấm.
*/
Item {
    id: root
    // Mỗi mục là { value, label }. `value` là thứ gửi lên máy chủ, `label` là thứ người đọc.
    property var options: []
    property var selected: []
    property string title: ""
    property bool searchable: false
    property string searchPlaceholder: Tr.phrase("Tìm...")
    property string emptyNote: ""
    property bool open: false
    signal toggled(string value, bool checked)
    signal cleared()

    property string filterText: ""
    readonly property var shown: root.options.filter(function (option) {
        return !root.filterText || option.label.toLowerCase().indexOf(root.filterText.toLowerCase()) >= 0;
    })
    readonly property string headLabel: {
        if (root.selected.length === 0)
            return root.title;
        const first = root.options.find(function (option) { return option.value === root.selected[0]; });
        const name = first ? first.label : root.selected[0];
        return root.selected.length > 1 ? name + " +" + (root.selected.length - 1) : name;
    }

    property point origin: Qt.point(0, 0)
    onOpenChanged: if (open) origin = root.mapToItem(null, 0, 0)

    height: 32

    Rectangle {
        id: head
        anchors.fill: parent
        radius: Theme.radiusSmall
        color: root.open || headHover.containsMouse ? Theme.surfaceHigh : Theme.surface
        border.width: 1
        border.color: root.open ? Theme.accent : (root.selected.length > 0 ? Theme.accent : Theme.border)
        Behavior on color { ColorAnimation { duration: Theme.quick } }

        Text {
            anchors { left: parent.left; leftMargin: 10; right: countPill.left; rightMargin: 6
                      verticalCenter: parent.verticalCenter }
            text: root.headLabel
            color: root.selected.length > 0 ? Theme.text : Theme.textMuted
            font.pixelSize: Theme.fontBody
            font.bold: root.selected.length > 0
            elide: Text.ElideRight
        }
        Rectangle {
            id: countPill
            objectName: "filterChipCount"
            visible: root.selected.length > 1
            anchors { right: clearMark.left; rightMargin: visible ? 6 : 0; verticalCenter: parent.verticalCenter }
            width: visible ? countText.width + 12 : 0
            height: 18
            radius: 0
            color: Theme.accentSoft
            border.color: Theme.accent
            Text {
                id: countText
                anchors.centerIn: parent
                text: root.selected.length
                color: Theme.accent; font.pixelSize: Theme.fontLabel; font.bold: true
            }
        }
        // Xoá hết ngay trên ô: không có nó người dùng phải bung khay rồi bỏ tick từng mục.
        Text {
            id: clearMark
            objectName: "filterChipClear"
            visible: root.selected.length > 0
            width: visible ? clearMetrics.width + 8 : 0
            anchors { right: arrow.left; verticalCenter: parent.verticalCenter }
            horizontalAlignment: Text.AlignHCenter
            text: "✕"
            color: clearHover.containsMouse ? Theme.danger : Theme.textMuted
            font.pixelSize: Theme.fontLabel
            TextMetrics { id: clearMetrics; font: clearMark.font; text: clearMark.text }
            MouseArea {
                id: clearHover
                anchors.fill: parent
                enabled: root.selected.length > 0
                hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                onClicked: root.cleared()
            }
        }
        Text {
            id: arrow
            anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
            text: "⌄"; color: Theme.textMuted; font.pixelSize: Theme.fontHeading
            rotation: root.open ? 180 : 0
            Behavior on rotation { NumberAnimation { duration: Theme.quick } }
        }
        MouseArea {
            id: headHover
            anchors { fill: parent; rightMargin: clearMark.width + 10 }
            hoverEnabled: true; cursorShape: Qt.PointingHandCursor
            onClicked: root.open = !root.open
        }
    }

    // Bấm ra ngoài thì đóng. Không có tấm này, khay mở rồi nằm lì đè lên kết quả cho tới khi
    // người dùng đoán ra là phải bấm lại đúng cái ô — đúng cái "vướng" mà người chơi kêu.
    MouseArea {
        parent: root.Window.window ? root.Window.window.contentItem : root
        anchors.fill: parent
        z: 999
        enabled: root.open
        visible: root.open
        onPressed: function (mouse) { root.open = false; mouse.accepted = true; }
    }

    Rectangle {
        id: tray
        objectName: "filterChipTray"
        parent: root.Window.window ? root.Window.window.contentItem : root
        z: 1000
        width: Math.max(root.width, 190)
        x: root.origin.x
        y: root.origin.y + head.height + 4
        height: root.open ? trayBody.height + 8 : 0
        visible: height > 0
        clip: true
        radius: Theme.radiusSmall
        color: Theme.surfaceHigh
        border.color: Theme.border
        border.width: 1
        Behavior on height {
            NumberAnimation { duration: root.open ? Theme.normal : Theme.quick
                              easing.type: root.open ? Easing.OutBack : Easing.InCubic
                              easing.overshoot: 1.6 }
        }
        MouseArea { anchors.fill: parent }  // nuốt bấm vào khe/viền khay

        Column {
            id: trayBody
            anchors { top: parent.top; left: parent.left; right: parent.right; margins: 4 }
            spacing: 4

            TextField {
                visible: root.searchable
                width: parent.width; height: visible ? 30 : 0
                placeholder: root.searchPlaceholder
                onTextChanged: root.filterText = text
            }
            // Cuộn được thay vì cắt bớt: danh mục Mojang có hàng trăm bản, cắt đi thì người
            // tìm bản cũ không bao giờ thấy nó.
            ListView {
                width: parent.width
                height: Math.min(root.shown.length, 9) * 26
                clip: true
                model: root.shown
                delegate: CheckRow {
                    width: ListView.view.width
                    label: modelData.label
                    checked: root.selected.indexOf(modelData.value) >= 0
                    onToggled: function (checked) { root.toggled(modelData.value, checked); }
                }
            }
            Text {
                visible: root.shown.length === 0
                width: parent.width; height: visible ? 24 : 0
                verticalAlignment: Text.AlignVCenter
                leftPadding: 8
                text: root.options.length === 0 ? root.emptyNote : Tr.phrase("Không có mục nào khớp.")
                color: Theme.textMuted; font.pixelSize: Theme.fontBody
            }
        }
    }
}
