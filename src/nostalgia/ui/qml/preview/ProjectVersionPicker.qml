import QtQuick
import "../" as Legacy

Column {
    id: root
    objectName: "projectVersionPicker"
    property var details: ({ versions: [], targets: [] })
    property string gameVersion: ""
    property string versionId: ""
    property string instanceId: ""
    property bool versionExpanded: false
    property Item menuBackdrop: GlassTheme.backdrop
    readonly property string pinnedInstanceId: contentBridge.browseInstanceId
    readonly property bool isPack: details.contentKind === "modpack"
    readonly property var targets: (details.targets || []).filter(function (target) {
        return !root.pinnedInstanceId || target.instanceId === root.pinnedInstanceId;
    })
    readonly property var selectedTarget: targets.find(function (target) {
        return target.instanceId === root.instanceId;
    }) || null
    readonly property var gameChoices: {
        var values = [];
        (details.versions || []).forEach(function (release) {
            release.gameVersions.forEach(function (game) {
                if (values.indexOf(game) < 0)
                    values.push(game);
            });
        });
        return root.pinnedInstanceId ? values.filter(function (game) {
            return game === contentBridge.gameVersion;
        }) : values;
    }
    // Backend dùng cùng quy tắc tương thích với bộ cài, kể cả Quilt/Fabric.
    readonly property var releases: (details.versions || []).filter(function (release) {
        return root.isPack ? release.gameVersions.indexOf(root.gameVersion) >= 0
            : !!root.selectedTarget && root.selectedTarget.versionIds.indexOf(release.versionId) >= 0;
    })
    readonly property var preferredRelease: stableFirst(releases)
    readonly property var createRelease: stableFirst(details.versions || [])
    readonly property var chosen: releases.find(function (release) {
        return release.versionId === root.versionId;
    }) || null
    readonly property bool canInstall: !!chosen && (isPack || !!selectedTarget)
    signal createRequested(string gameVersion, string loaderKind)
    spacing: 12

    // API trả bản mới nhất trước; ưu tiên bản ổn định trong danh sách đã lọc.
    function stableFirst(versions) {
        return versions.find(function (release) { return release.type === "release"; }) || versions[0] || null;
    }
    function reconcile() {
        if (isPack) {
            if (gameChoices.indexOf(gameVersion) < 0)
                gameVersion = gameChoices.indexOf(contentBridge.gameVersion) >= 0 ? contentBridge.gameVersion : gameChoices[0] || "";
        } else {
            if (!selectedTarget)
                instanceId = pinnedInstanceId && targets.length ? targets[0].instanceId : "";
            gameVersion = selectedTarget ? selectedTarget.gameVersion : "";
        }
        if (!chosen)
            versionId = preferredRelease ? preferredRelease.versionId : "";
    }
    function reset() {
        versionExpanded = false;
        gameVersion = "";
        versionId = "";
        instanceId = "";
        reconcile();
    }
    function targetLabel(target) {
        var instance = bridge.instances.find(function (instance) {
            return instance.instanceId === target.instanceId;
        });
        return (instance ? instance.label : target.instanceId) + "  ·  " + target.gameVersion + "  ·  " + target.loaderKind;
    }
    function targetIndex() {
        return Math.max(0, targets.findIndex(function (target) {
            return target.instanceId === root.instanceId;
        }) + (pinnedInstanceId ? 0 : 1));
    }
    function releaseIndex() {
        return Math.max(0, releases.findIndex(function (release) {
            return release.versionId === root.versionId;
        }));
    }
    function releaseLabel(release) {
        return release.number + "  ·  " + release.type + (release.loaders.length && (details.contentKind === "mod" || isPack) ? "  ·  " + release.loaders.join(" / ") : "");
    }
    function synchronizeChoices() {
        targetSelect.currentIndex = Qt.binding(function () { return root.targetIndex(); });
        releaseSelect.currentIndex = Qt.binding(function () { return root.releaseIndex(); });
    }
    onDetailsChanged: Qt.callLater(root.reconcile)
    onGameVersionChanged: Qt.callLater(root.reconcile)
    onVersionIdChanged: Qt.callLater(root.synchronizeChoices)
    onPinnedInstanceIdChanged: Qt.callLater(root.reset)
    onInstanceIdChanged: {
        versionId = "";
        versionExpanded = false;
        Qt.callLater(root.reconcile);
        Qt.callLater(root.synchronizeChoices);
    }

    Column {
        width: parent.width
        spacing: 7
        visible: !root.isPack
        Text {
            text: Legacy.Tr.phrase("Cài vào bản chơi")
            color: GlassTheme.text
            font.pixelSize: GlassTheme.fontSubheading
            font.weight: Font.DemiBold
            font.family: GlassTheme.font
        }
        Select {
            id: targetSelect
            objectName: "projectTarget"
            menuBackdrop: root.menuBackdrop
            width: parent.width
            model: (root.pinnedInstanceId ? [] : [Legacy.Tr.phrase("Chọn bản chơi")]).concat(root.targets.map(function (target) {
                return root.targetLabel(target);
            }))
            displayText: root.selectedTarget ? root.targetLabel(root.selectedTarget) : root.targets.length ? Legacy.Tr.phrase("Chọn bản chơi") : Legacy.Tr.phrase("Chưa có bản chơi")
            currentIndex: root.targetIndex()
            // ComboBox đặt lại chỉ số khi model đổi (kể cả đổi ngôn ngữ).
            onModelChanged: Qt.callLater(root.synchronizeChoices)
            enabled: root.targets.length > 0 && !projectBridge.installing && !root.pinnedInstanceId
            onActivated: function (index) {
                var target = root.targets[index - (root.pinnedInstanceId ? 0 : 1)];
                root.instanceId = target ? target.instanceId : "";
            }
        }
    }
    Item {
        width: parent.width
        height: Math.max(releaseSummary.implicitHeight + 20, changeVersion.height + 12)
        visible: !root.isPack && !!root.chosen
        Rectangle {
            anchors.fill: parent
            radius: 12
            color: GlassTheme.alpha(GlassTheme.surface, 0.35)
            border.color: GlassTheme.stroke
        }
        Column {
            id: releaseSummary
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.right: changeVersion.left
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4
            Text {
                width: parent.width
                text: root.chosen && root.preferredRelease && root.chosen.versionId === root.preferredRelease.versionId
                    ? Legacy.Tr.phrase("Phiên bản đề xuất") : Legacy.Tr.phrase("Phiên bản đã chọn")
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: GlassTheme.fontLabel
            }
            Text {
                objectName: "projectSelectedRelease"
                width: parent.width
                text: root.chosen ? root.chosen.number + "  ·  " + root.chosen.type : ""
                color: GlassTheme.text
                font.family: GlassTheme.font
                font.pixelSize: GlassTheme.fontBody
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }
        }
        Button {
            id: changeVersion
            objectName: "projectChangeVersion"
            anchors.right: parent.right
            anchors.rightMargin: 6
            anchors.verticalCenter: parent.verticalCenter
            label: root.versionExpanded ? Legacy.Tr.phrase("Thu gọn") : Legacy.Tr.phrase("Đổi phiên bản")
            quiet: true
            clickable: !projectBridge.installing
            onClicked: root.versionExpanded = !root.versionExpanded
        }
    }
    Text {
        visible: root.isPack
        text: Legacy.Tr.phrase("Phiên bản cài đặt")
        color: GlassTheme.text
        font.family: GlassTheme.font
        font.pixelSize: GlassTheme.fontSubheading
        font.weight: Font.DemiBold
    }
    Row {
        width: parent.width
        spacing: 12
        visible: root.isPack || root.versionExpanded
        Column {
            width: (parent.width - 12) * 0.34
            spacing: 7
            visible: root.isPack
            Text {
                text: "Minecraft"
                color: GlassTheme.muted
                font.pixelSize: GlassTheme.fontLabel
                font.family: GlassTheme.font
            }
            Select {
                objectName: "projectGameVersion"
                menuBackdrop: root.menuBackdrop
                searchPlaceholder: Legacy.Tr.phrase("Tìm Minecraft…")
                width: parent.width
                model: root.gameChoices
                currentIndex: Math.max(0, root.gameChoices.indexOf(root.gameVersion))
                enabled: model.length > 0 && !projectBridge.installing && !root.pinnedInstanceId
                onActivated: function (index) { root.gameVersion = root.gameChoices[index]; }
            }
        }
        Column {
            width: root.isPack ? (parent.width - 12) * 0.66 : parent.width
            spacing: 7
            Text {
                text: Legacy.Tr.phrase("Bản phát hành")
                color: GlassTheme.muted
                font.pixelSize: GlassTheme.fontLabel
                font.family: GlassTheme.font
            }
            Select {
                id: releaseSelect
                objectName: "projectRelease"
                menuBackdrop: root.menuBackdrop
                searchPlaceholder: Legacy.Tr.phrase("Tìm bản phát hành…")
                width: parent.width
                model: root.releases.map(function (release) {
                    return root.releaseLabel(release);
                })
                displayText: root.chosen ? root.releaseLabel(root.chosen) : ""
                currentIndex: root.releaseIndex()
                onModelChanged: Qt.callLater(root.synchronizeChoices)
                enabled: model.length > 0 && !projectBridge.installing
                onActivated: function (index) { root.versionId = root.releases[index].versionId; }
            }
        }
    }
    Button {
        objectName: "projectUseRecommended"
        visible: !root.isPack && root.versionExpanded && !!root.chosen && !!root.preferredRelease && root.chosen.versionId !== root.preferredRelease.versionId
        label: Legacy.Tr.phrase("Dùng bản đề xuất")
        quiet: true
        clickable: !projectBridge.installing
        onClicked: root.versionId = root.preferredRelease.versionId
    }
    Text {
        objectName: "projectCompatibilityNote"
        width: parent.width
        visible: root.isPack || !!root.selectedTarget
        text: root.isPack ? Legacy.Tr.phrase("Tạo bản chơi mới với Minecraft và loader do modpack quy định.")
            : !root.chosen ? Legacy.Tr.phrase("Không có bản phát hành phù hợp với bản chơi này. Hãy thử dự án khác.")
            : root.details.contentKind === "mod" ? Legacy.Tr.phrase("Đã lọc phiên bản theo Minecraft và loader của bản chơi. Bạn có thể đổi phiên bản trước khi cài.")
            : Legacy.Tr.phrase("Đã lọc phiên bản theo Minecraft của bản chơi. Bạn có thể đổi phiên bản trước khi cài.")
        color: root.selectedTarget && !root.chosen ? GlassTheme.danger : GlassTheme.muted
        font.family: GlassTheme.font
        font.pixelSize: GlassTheme.fontLabel
        wrapMode: Text.Wrap
        lineHeight: 1.3
    }
    Button {
        objectName: "projectCreateCompatible"
        visible: !!root.createRelease && !root.isPack && !root.pinnedInstanceId && (!root.targets.length || (!!root.selectedTarget && !root.releases.length))
        label: Legacy.Tr.phrase("Tạo bản chơi phù hợp  ↗")
        quiet: true
        clickable: !projectBridge.installing
        onClicked: root.createRequested(root.createRelease.gameVersions[0], root.details.contentKind === "mod" ? root.createRelease.loaders[0] : "vanilla")
    }
}
