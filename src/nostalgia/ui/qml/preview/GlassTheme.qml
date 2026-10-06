pragma Singleton
import QtQuick
import "../" as Legacy

QtObject {
    // Reuse the existing launcher palette so every page keeps its original identity.
    readonly property color background: Legacy.Theme.background
    readonly property color surface: Legacy.Theme.surface
    readonly property color raised: Legacy.Theme.surfaceHigh
    readonly property color stroke: Legacy.Theme.border
    readonly property color text: Legacy.Theme.text
    readonly property color muted: Legacy.Theme.textMuted
    readonly property color accent: Legacy.Theme.accent
    readonly property color brand: Legacy.Theme.brand
    readonly property color danger: Legacy.Theme.danger
    readonly property color selectedSurface: Legacy.Theme.accentSoft
    readonly property color primaryFace: Qt.darker(accent, 2.0)
    readonly property color primaryHover: Qt.lighter(primaryFace, 1.08)
    readonly property color canvas: Legacy.Theme.mix(background, accent, 0.06)
    readonly property color glassSurface: alpha(surface, 0.80)
    readonly property color cardSurface: alpha(surface, 0.74)
    readonly property color inputSurface: alpha(raised, 0.65)
    readonly property string font: "Inter"
    readonly property string displayFont: "Manrope"
    property var preferences: null
    readonly property bool reducedMotion: preferences ? preferences.reducedMotion : false
    readonly property real scale: preferences ? preferences.uiScale / 100 : 1
    readonly property int fontCaption: Math.round(10 * scale)
    readonly property int fontNote: Math.round(11 * scale)
    readonly property int fontLabel: Math.round(12 * scale)
    readonly property int fontBody: Math.round(13 * scale)
    readonly property int fontControl: Math.round(14 * scale)
    readonly property int fontSubheading: Math.round(15 * scale)
    readonly property int fontHeading: Math.round(17 * scale)
    readonly property int fontLead: Math.round(19 * scale)
    readonly property int fontTitle: Math.round(22 * scale)
    readonly property int fontDialog: Math.round(24 * scale)
    readonly property int fontPage: Math.round(30 * scale)
    readonly property int fontPrice: Math.round(44 * scale)
    readonly property int fontMicro: Math.round(9 * scale)
    readonly property int fontAction: Math.round(16 * scale)
    readonly property int fontSection: Math.round(18 * scale)
    readonly property int fontBrand: Math.round(21 * scale)
    readonly property int fontLogin: Math.round(25 * scale)
    readonly property int fontResult: Math.round(26 * scale)
    readonly property int fontCode: Math.round(32 * scale)
    readonly property int normal: reducedMotion ? 0 : 260
    readonly property int slow: reducedMotion ? 0 : 380
    readonly property int quick: reducedMotion ? 0 : 160
    property var backdrop: null
    function alpha(color, opacity) {
        return Qt.rgba(color.r, color.g, color.b, opacity);
    }
}
