import QtQuick
import "../" as Legacy

Legacy.Main {
    socialPreview: true
    Component.onCompleted: {
        GlassTheme.preferences = settingsBridge;
        GlassTheme.backdrop = null;
    }
}
