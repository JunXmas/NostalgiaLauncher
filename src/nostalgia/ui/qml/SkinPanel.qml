import QtQuick
import "preview" as Preview

Preview.Glass {
    id: skinPanel
    property var shown: ({})
    property bool hasShown: false
    property string tab: "skin"
    readonly property var draft: skinEditor.details
    padding: 20
    onShownChanged: if (hasShown) skinEditor.showAccount(shown.accountId)
    onHasShownChanged: skinEditor.showAccount(hasShown ? shown.accountId : "")
    Component.onCompleted: if (hasShown) skinEditor.showAccount(shown.accountId)
    Preview.MotionTabs {
        id: tabs
        width: Math.max(100, parent.width - help.width - 12); labels: ["Skin", "Cape"]
        currentIndex: skinPanel.tab === "skin" ? 0 : 1; namePrefix: "skinSection-"
        onSelected: function(index) { skinPanel.tab = index === 0 ? "skin" : "cape"; }
    }
    Preview.GuideButton { id: help; anchors.right: parent.right; topicId: "appearance" }
    Preview.PaymentText {
        id: caption
        anchors.top: tabs.bottom; anchors.topMargin: 12
        width: parent.width
        text: skinPanel.tab === "skin" ? "Chọn skin, xem trước rồi lưu cho tài khoản đang chọn." :
              skinPanel.shown.accountKind === "microsoft" ? "Thử áo choàng đã sở hữu trên nhân vật trước khi lưu." :
              skinPanel.shown.accountKind === "ely" ? "Áo choàng đang dùng trên Ely.by. Thay cape tại ely.by." : "Tài khoản ngoại tuyến chưa có cape."
        color: Theme.textMuted; font.pixelSize: Theme.fontBody
    }
    Row {
        id: controls
        anchors.top: caption.bottom; anchors.topMargin: 12; spacing: 12
        visible: skinPanel.hasShown && skinPanel.tab === "skin"
        Toggle {
            objectName: "skinSlimToggle"
            anchors.verticalCenter: parent.verticalCenter
            checked: skinPanel.draft.slim || false
            enabled: !skinEditor.busy
            accessibleLabel: "Dáng tay Slim"
            onToggled: function(checked) { skinEditor.setSlim(checked); }
        }
        Preview.PaymentText {
            objectName: "skinModelLabel"
            anchors.verticalCenter: parent.verticalCenter
            text: skinPanel.draft.slim ? "Slim · tay 3 px" : "Classic · tay 4 px"
        }
    }
    Preview.InertialScroll {
        id: skinScroll; objectName: "skinLibraryScroll"
        anchors.top: controls.visible ? controls.bottom : caption.bottom
        anchors.topMargin: 16; anchors.left: parent.left; anchors.right: parent.right
        anchors.bottom: footer.top; anchors.bottomMargin: 16
        contentHeight: skinColumn.implicitHeight
        Column {
            id: skinColumn; width: skinScroll.width; spacing: 14
            SkinLibrary {
                width: parent.width; visible: skinPanel.tab === "skin"
                shown: skinPanel.shown; hasShown: skinPanel.hasShown; viewport: skinScroll
            }
            CapeLibrary {
                width: parent.width; visible: skinPanel.hasShown && skinPanel.tab === "cape"
                shown: skinPanel.shown; viewport: skinScroll
            }
        }
    }
    Column {
        id: footer
        anchors.bottom: parent.bottom; width: parent.width; spacing: 10
        Preview.PaymentText {
            objectName: "appearanceStatus"
            width: parent.width; visible: text.length > 0
            text: skinEditor.busy ? "Đang lưu…" : skinPanel.draft.note || ""
            color: Theme.textMuted; font.pixelSize: Theme.fontLabel
        }
        Flow {
            width: parent.width; spacing: 8
            Preview.Button { objectName: "skinSaveButton"; label: "Lưu thay đổi"; primary: true; clickable: skinPanel.hasShown && skinPanel.draft.dirty && !skinEditor.busy && !accountBridge.busy && !capeBridge.busy; onClicked: skinEditor.save() }
            Preview.Button { objectName: "skinDiscardButton"; label: "Hủy thay đổi"; visible: skinPanel.draft.dirty; clickable: !skinEditor.busy; onClicked: skinEditor.discard() }
            Preview.Button { objectName: "skinRefreshButton"; label: "Làm mới"; quiet: true; visible: skinPanel.hasShown && skinPanel.shown.accountKind !== "offline"; clickable: !skinEditor.busy && !accountBridge.busy && !skinPanel.draft.dirty; onClicked: { accountBridge.refreshSkins(); if (skinPanel.tab === "cape") capeBridge.loadCapes(skinPanel.shown.accountId); } }
        }
    }
}
