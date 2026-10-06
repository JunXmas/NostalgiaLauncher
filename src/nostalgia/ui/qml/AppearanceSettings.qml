import QtQuick

Panel {
    id: root
    implicitHeight: contentTop + body.height + Theme.pad
    function apply(scale, compact, reduced, background, language) {
        settingsBridge.setAppearance(scale, compact, reduced, background, language);
    }
    Column {
        id: body
        anchors { left: parent.left; right: parent.right; top: parent.top }
        spacing: 14
        SectionTitle { objectName: "appearanceHeading"; caption: Tr.phrase("Giao diện & ngôn ngữ") }
        Flow {
            width: parent.width; spacing: 12
            Text { text: Tr.phrase("Cỡ chữ"); font.pixelSize: Theme.fontBody; color: Theme.text; height: 36; verticalAlignment: Text.AlignVCenter }
            Dropdown {
                objectName: "textScalePicker"; width: 140
                model: ["100%", "125%", "150%"]
                currentIndex: [100,125,150].indexOf(settingsBridge.uiScale)
                onActivated: function(index) { root.apply([100,125,150][index], settingsBridge.compactUi, settingsBridge.reducedMotion, settingsBridge.decorativeBackground, settingsBridge.language); }
            }
            Text { text: Tr.phrase("Ngôn ngữ"); font.pixelSize: Theme.fontBody; color: Theme.text; height: 36; verticalAlignment: Text.AlignVCenter }
            Dropdown {
                objectName: "languagePicker"; width: 170
                model: [Tr.phrase("Tiếng Việt"), "English"]
                currentIndex: settingsBridge.language === "en" ? 1 : 0
                onActivated: function(index) { root.apply(settingsBridge.uiScale, settingsBridge.compactUi, settingsBridge.reducedMotion, settingsBridge.decorativeBackground, index === 1 ? "en" : "vi"); }
            }
        }
        Row {
            spacing: 14
            Toggle { objectName: "compactUiToggle"; accessibleLabel: Tr.phrase("Danh sách bản chơi gọn"); checked: settingsBridge.compactUi; onToggled: function(value) { root.apply(settingsBridge.uiScale,value,settingsBridge.reducedMotion,settingsBridge.decorativeBackground,settingsBridge.language); } }
            Text { text: Tr.phrase("Danh sách bản chơi gọn"); color: Theme.text; font.pixelSize: Theme.fontBody; anchors.verticalCenter: parent.verticalCenter }
        }
        Row {
            spacing: 14
            Toggle { objectName: "reducedMotionToggle"; accessibleLabel: Tr.phrase("Giảm chuyển động"); checked: settingsBridge.reducedMotion; onToggled: function(value) { root.apply(settingsBridge.uiScale,settingsBridge.compactUi,value,settingsBridge.decorativeBackground,settingsBridge.language); } }
            Text { text: Tr.phrase("Giảm chuyển động"); color: Theme.text; font.pixelSize: Theme.fontBody; anchors.verticalCenter: parent.verticalCenter }
        }
        Row {
            spacing: 14
            Toggle { objectName: "decorativeBackgroundToggle"; accessibleLabel: Tr.phrase("Ảnh nền trang chủ"); checked: settingsBridge.decorativeBackground; onToggled: function(value) { root.apply(settingsBridge.uiScale,settingsBridge.compactUi,settingsBridge.reducedMotion,value,settingsBridge.language); } }
            Text { text: Tr.phrase("Ảnh nền trang chủ"); color: Theme.text; font.pixelSize: Theme.fontBody; anchors.verticalCenter: parent.verticalCenter }
        }
        Text { width: parent.width; wrapMode: Text.WordWrap; text: Tr.phrase("Thay đổi áp dụng ngay và được lưu cho lần mở tiếp theo."); color: Theme.textMuted; font.pixelSize: Theme.fontLabel }
    }
}
