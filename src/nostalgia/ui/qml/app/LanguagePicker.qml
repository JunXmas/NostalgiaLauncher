import QtQuick
import "../" as Legacy

Select {
    objectName: "welcomeLanguagePicker"
    width: 146 * GlassTheme.scale
    model: ["Tiếng Việt", "English"]
    currentIndex: settingsBridge.language === "en" ? 1 : 0
    Accessible.name: Legacy.Tr.phrase("Ngôn ngữ")
    onActivated: function(index) {
        settingsBridge.setAppearance(settingsBridge.uiScale, settingsBridge.compactUi,
            settingsBridge.reducedMotion, settingsBridge.decorativeBackground, index === 1 ? "en" : "vi");
    }
}
