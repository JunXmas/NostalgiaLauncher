import QtQuick
import "../" as Legacy
import "GuideCatalog.js" as Guides

Item {
    id: root
    objectName: "minimalPreview"
    implicitWidth: 1440
    implicitHeight: 900
    property int currentIndex: 0
    property bool sessionSkipped: false
    property bool advancedLibrary: false
    Shortcut { sequence: "F1"; onActivated: GuideCenter.show(root.loginVisible ? "start" : root.currentIndex === 1 && pages.item && pages.item.serverMode ? "server" : Guides.pageTopic(root.currentIndex)) }
    GuideDialog {}
    LocalModDialog {}
    readonly property bool loginVisible: (!bridge.activePlayerName && !sessionSkipped) || googleLinkBridge.pending
    Component.onCompleted: {
        GlassTheme.preferences = settingsBridge;
        GlassTheme.backdrop = ambient;
        Legacy.Theme.modern = true;
        Legacy.Theme.modalBackdrop = scene;
        Legacy.Theme.preferences = settingsBridge;
        Legacy.Tr.setLanguage(settingsBridge.language);
    }
    Connections {
        target: settingsBridge
        function onAppearanceChanged() { Legacy.Tr.setLanguage(settingsBridge.language); }
    }
    Binding {
        target: Legacy.Theme
        property: "page"
        value: root.loginVisible ? 0 : root.currentIndex === 7 ? 3 : root.currentIndex
    }
    Binding { target: GlassTheme; property: "pageMotion"; value: pageOffset.y }
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
                onLoaded: pageEntrance.restart()
                transform: Translate { id: pageOffset }
                SequentialAnimation {
                    id: pageEntrance
                    ParallelAnimation {
                        NumberAnimation { target: pages; property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal; easing.type: Easing.OutCubic }
                        NumberAnimation { target: pageOffset; property: "y"; from: GlassTheme.reducedMotion ? 0 : 12; to: 0; duration: GlassTheme.normal; easing.type: Easing.OutCubic }
                    }
                }
                source: {
                    if (root.currentIndex === 0)
                        return "Home.qml";
                    if (root.currentIndex === 1)
                        return "Instances.qml";
                    if (root.currentIndex === 4)
                        return "Friends.qml";
                    if (root.currentIndex === 7)
                        return "CosmeticLibrary.qml";
                    if (root.currentIndex === 3)
                        return "Accounts.qml";
                    if (root.currentIndex === 2)
                        return "Library.qml";
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
    Glass {
        visible: !root.loginVisible && root.currentIndex !== 4 && socialBridge.invitations.length > 0
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 24
        width: Math.min(380 * GlassTheme.scale, parent.width - 48)
        height: invitationNote.implicitHeight + invitationOpen.height + 50
        padding: 18
        z: 140
        Column {
            width: parent.width
            spacing: 12
            PaymentText { id: invitationNote; width: parent.width; text: socialBridge.invitations.length ? socialBridge.invitations[0].name + Legacy.Tr.phrase(" mời bạn chơi cùng") : "" }
            Button { id: invitationOpen; label: Legacy.Tr.phrase("Xem lời mời"); primary: true; onClicked: root.navigate(4) }
        }
    }
    Loader {
        anchors.fill: parent
        z: 145
        active: draftReviewPanel.length > 0
        source: draftReviewPanel
    }
    Login {
        objectName: "minimalLogin"
        anchors.fill: parent
        visible: root.loginVisible && !googleLinkBridge.pending
        onEnterRequested: {
            root.sessionSkipped = true;
            root.navigate(2);
        }
    }
    GoogleLink { anchors.fill: parent; visible: googleLinkBridge.pending }
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
    HostDialog { backdrop: scene }
    GuestSyncDialog { backdrop: scene }
    SupportDialog {
        id: support
        backdrop: scene
        onDonateRequested: donateDialog.open()
    }
    ModernCreateInstanceDialog {
        id: createForProject
        objectName: "projectCreateInstance"
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
    SocialProfileDialog { id: socialProfileDialog }
    UpdateNotice { anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 24; z: 135; visible: active && !root.loginVisible; onDetailsRequested: updateDetails.open() }
    UpdateDialog { id: updateDetails; backdrop: scene }
    Legacy.ConfirmDialog {
        objectName: "confirmDialog"
        anchors.fill: parent
    }
    Legacy.DonateDialog {
        objectName: "donateDialog"
        anchors.fill: parent
    }
    Legacy.LoadingToast {
        suppressLauncherBusy: hostBridge.details.active && hostBridge.details.deferred && ["lobby", "publishing", "error"].indexOf(hostBridge.details.stage) >= 0
        z: 120
    }
}
