import QtQuick
import "../" as Legacy

Item {
    id: root
    objectName: "minimalPreview"
    implicitWidth: 1440
    implicitHeight: 900
    property int currentIndex: 0
    property bool sessionSkipped: false
    property bool advancedLibrary: false
    readonly property bool loginVisible: !bridge.activePlayerName && !sessionSkipped
    Component.onCompleted: {
        GlassTheme.preferences = settingsBridge;
        GlassTheme.backdrop = ambient;
        Legacy.Theme.preferences = settingsBridge;
        Legacy.Tr.setLanguage(settingsBridge.language);
    }
    Binding {
        target: Legacy.Theme
        property: "page"
        value: root.loginVisible ? 0 : root.currentIndex
    }
    function navigate(index) {
        currentIndex = index;
        advancedLibrary = false;
    }
    Item {
        id: scene
        objectName: "previewScene"
        anchors.fill: parent
        Ambient {
            id: ambient
            anchors.fill: parent
            cinematic: root.loginVisible
        }
        Item {
            anchors.fill: parent
            visible: !root.loginVisible
            Navigation {
                id: navigation
                objectName: "minimalNavigation"
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.margins: 16
                width: Math.min(275, 212 * Math.max(1, GlassTheme.scale * 0.9))
                currentIndex: root.currentIndex
                onSupportRequested: support.open()
                onNavigate: function (index) {
                    root.navigate(index);
                }
            }
            Loader {
                id: pages
                objectName: "minimalPageLoader"
                anchors.left: navigation.right
                anchors.leftMargin: 32
                anchors.right: parent.right
                anchors.rightMargin: 40
                anchors.top: parent.top
                anchors.topMargin: 30
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 24
                source: {
                    if (root.currentIndex === 0)
                        return "Home.qml";
                    if (root.currentIndex === 1)
                        return "Instances.qml";
                    if (root.currentIndex === 2)
                        return root.advancedLibrary ? "../pages/LibraryPage.qml" : "Library.qml";
                    return "../pages/" + ["HomePage.qml", "InstancesPage.qml", "LibraryPage.qml", "AccountsPage.qml", "MultiplayerPage.qml", "LogPage.qml", "SettingsPage.qml"][root.currentIndex];
                }
                Connections {
                    target: pages.item
                    ignoreUnknownSignals: true
                    function onNavigate(index) {
                        root.navigate(index);
                    }
                    function onAdvancedRequested() {
                        root.advancedLibrary = true;
                    }
                }
            }
        }
    }
    Login {
        objectName: "minimalLogin"
        anchors.fill: parent
        visible: root.loginVisible
        onEnterRequested: {
            root.sessionSkipped = true;
            root.navigate(2);
        }
    }
    DeviceLogin {
        anchors.fill: parent
    }
    ProjectDialog {
        id: projectDialog
        backdrop: scene
        onCreateRequested: function (gameVersion, loaderKind) {
            projectDialog.close();
            createForProject.openDialog();
            createForProject.loaderKind = loaderKind;
            createForProject.pickGameVersion(gameVersion);
            createForProject.expandedMajor = gameVersion.split(".").slice(0, 2).join(".");
        }
    }
    SupportDialog {
        id: support
        backdrop: scene
        onDonateRequested: donateDialog.open()
    }
    Legacy.CreateInstanceDialog {
        id: createForProject
        objectName: "projectCreateInstance"
        anchors.fill: parent
        onVisibleChanged: {
            if (!visible && projectDialog.openedProject) {
                projectBridge.refreshTargets();
                projectDialog.open();
            }
        }
    }
    Legacy.RecoveryBanner {
        id: recovery
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 24
        z: 150
    }
    Connections {
        target: bridge
        function onFailed(message) {
            if (!root.loginVisible)
                recovery.report(message, bridge);
        }
    }
    Connections {
        target: contentBridge
        function onFailed(message) {
            recovery.report(message, contentBridge);
        }
    }
    Connections {
        target: storageBridge
        function onFailed(message) {
            recovery.report(message, storageBridge);
        }
    }
    Connections {
        target: accountBridge
        function onFailed(message) {
            if (!root.loginVisible)
                recovery.report(message, accountBridge);
        }
    }
    Legacy.ConfirmDialog {
        objectName: "confirmDialog"
        anchors.fill: parent
    }
    Legacy.DonateDialog {
        objectName: "donateDialog"
        anchors.fill: parent
    }
    Legacy.LoadingToast {
        z: 120
    }
}
