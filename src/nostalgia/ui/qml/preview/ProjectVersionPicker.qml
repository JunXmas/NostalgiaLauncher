import QtQuick

Column {
    id: root
    objectName: "projectVersionPicker"
    property var details: ({
            versions: [],
            targets: []
        })
    property string gameVersion: ""
    property string versionId: ""
    property string instanceId: ""
    property Item menuBackdrop: GlassTheme.backdrop
    readonly property bool isPack: details.contentKind === "modpack"
    readonly property var gameChoices: {
        var values = [];
        (details.versions || []).forEach(function (release) {
            release.gameVersions.forEach(function (game) {
                if (values.indexOf(game) < 0)
                    values.push(game);
            });
        });
        return values;
    }
    readonly property var releases: (details.versions || []).filter(function (release) {
        return release.gameVersions.indexOf(root.gameVersion) >= 0;
    })
    readonly property var chosen: releases.find(function (release) {
        return release.versionId === root.versionId;
    }) || null
    readonly property var targets: (details.targets || []).filter(function (target) {
        if (!root.chosen || target.gameVersion !== root.gameVersion)
            return false;
        if (details.contentKind !== "mod")
            return true;
        return root.chosen.loaders.indexOf(target.loaderKind) >= 0 || (target.loaderKind === "quilt" && root.chosen.loaders.indexOf("fabric") >= 0);
    })
    readonly property bool canInstall: !!chosen && (isPack || targets.some(function (target) {
            return target.instanceId === root.instanceId;
        }))
    signal createRequested(string gameVersion, string loaderKind)
    spacing: 12
    function reconcile() {
        if (gameChoices.indexOf(gameVersion) < 0)
            gameVersion = gameChoices.indexOf(contentBridge.gameVersion) >= 0 ? contentBridge.gameVersion : gameChoices[0] || "";
        if (!chosen) {
            var compatible = releases.filter(function (release) {
                return details.contentKind !== "mod" || !contentBridge.loaderKind || release.loaders.indexOf(contentBridge.loaderKind) >= 0 || (contentBridge.loaderKind === "quilt" && release.loaders.indexOf("fabric") >= 0);
            });
            var pool = compatible.length ? compatible : releases;
            var preferred = pool.find(function (release) {
                return release.type === "release";
            }) || pool[0];
            versionId = preferred ? preferred.versionId : "";
        }
        if (!targets.some(function (target) {
            return target.instanceId === root.instanceId;
        })) {
            var preferredTarget = targets.find(function (target) {
                return target.instanceId === contentBridge.instanceId;
            }) || targets[0];
            instanceId = preferredTarget ? preferredTarget.instanceId : "";
        }
    }
    function reset() {
        gameVersion = "";
        versionId = "";
        instanceId = "";
        reconcile();
    }
    function targetLabel(target) {
        var instance = bridge.instances.find(function (instance) {
            return instance.instanceId === target.instanceId;
        });
        return (instance ? instance.label : target.instanceId) + "  ·  " + target.loaderKind;
    }
    onDetailsChanged: Qt.callLater(root.reconcile)
    onGameVersionChanged: Qt.callLater(root.reconcile)
    onVersionIdChanged: Qt.callLater(root.reconcile)
    Text {
        text: "Phiên bản cài đặt"
        color: GlassTheme.text
        font.family: GlassTheme.font
        font.pixelSize: GlassTheme.fontSubheading
        font.weight: Font.DemiBold
    }
    Row {
        width: parent.width
        spacing: 12
        Column {
            width: (parent.width - 12) * 0.34
            spacing: 7
            Text {
                text: "Minecraft"
                color: GlassTheme.muted
                font.pixelSize: GlassTheme.fontLabel
                font.family: GlassTheme.font
            }
            Select {
                objectName: "projectGameVersion"
                menuBackdrop: root.menuBackdrop
                searchPlaceholder: "Tìm Minecraft…"
                width: parent.width
                model: root.gameChoices
                currentIndex: Math.max(0, root.gameChoices.indexOf(root.gameVersion))
                enabled: model.length > 0 && !projectBridge.installing
                onActivated: function (index) {
                    root.gameVersion = root.gameChoices[index];
                }
            }
        }
        Column {
            width: (parent.width - 12) * 0.66
            spacing: 7
            Text {
                text: "Bản phát hành"
                color: GlassTheme.muted
                font.pixelSize: GlassTheme.fontLabel
                font.family: GlassTheme.font
            }
            Select {
                objectName: "projectRelease"
                menuBackdrop: root.menuBackdrop
                searchPlaceholder: "Tìm bản phát hành…"
                width: parent.width
                model: root.releases.map(function (release) {
                    return release.number + "  ·  " + release.type + (release.loaders.length && (root.details.contentKind === "mod" || root.isPack) ? "  ·  " + release.loaders.join(" / ") : "");
                })
                currentIndex: Math.max(0, root.releases.findIndex(function (release) {
                    return release.versionId === root.versionId;
                }))
                enabled: model.length > 0 && !projectBridge.installing
                onActivated: function (index) {
                    root.versionId = root.releases[index].versionId;
                }
            }
        }
    }
    Column {
        width: parent.width
        spacing: 7
        visible: !root.isPack
        Text {
            text: "Cài vào bản chơi"
            color: GlassTheme.muted
            font.pixelSize: GlassTheme.fontLabel
            font.family: GlassTheme.font
        }
        Select {
            objectName: "projectTarget"
            menuBackdrop: root.menuBackdrop
            width: parent.width
            model: root.targets.map(function (target) {
                return root.targetLabel(target);
            })
            displayText: root.targets.length ? currentText : "Chưa có bản chơi tương thích"
            currentIndex: Math.max(0, root.targets.findIndex(function (target) {
                return target.instanceId === root.instanceId;
            }))
            enabled: root.targets.length > 0 && !projectBridge.installing
            onActivated: function (index) {
                root.instanceId = root.targets[index].instanceId;
            }
        }
    }
    Text {
        width: parent.width
        visible: !!root.chosen
        text: !root.chosen ? "" : root.isPack ? "Tạo bản chơi mới với Minecraft và loader do modpack quy định." : root.targets.length ? "Chỉ hiện bản chơi khớp phiên bản Minecraft" + (root.details.contentKind === "mod" ? " và mod loader." : ".") : "Bạn cần một bản chơi Minecraft " + root.gameVersion + (root.details.contentKind === "mod" ? " với " + root.chosen.loaders.join(" / ") : "") + " để cài bản này."
        color: GlassTheme.muted
        font.family: GlassTheme.font
        font.pixelSize: GlassTheme.fontLabel
        wrapMode: Text.Wrap
        lineHeight: 1.3
    }
    Button {
        objectName: "projectCreateCompatible"
        visible: !!root.chosen && !root.isPack && root.targets.length === 0
        label: "Tạo bản chơi phù hợp  ↗"
        quiet: true
        clickable: !projectBridge.installing
        onClicked: root.createRequested(root.gameVersion, root.details.contentKind === "mod" ? root.chosen.loaders[0] : "vanilla")
    }
}
