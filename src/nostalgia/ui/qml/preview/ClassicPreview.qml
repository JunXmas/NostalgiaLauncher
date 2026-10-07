import QtQuick
import "../" as Legacy

Legacy.Main {
    socialPreview: true
    HostDialog { }
    Component.onCompleted: {
        GlassTheme.preferences = settingsBridge;
        GlassTheme.backdrop = null;
    }
}
