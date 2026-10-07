import QtQuick
import "preview" as Preview

/*
  Ô Skin/Cape: tab, mô tả, nút làm mới, thư viện skin (nút "Thêm skin" duy nhất nằm ở đó)
  và xem trước cape. Tách khỏi AccountsPage để giữ mỗi file ≤ 200 dòng.
*/
Panel {
    id: skinPanel
    property var shown: ({})
    property bool hasShown: false
    property string tab: "skin"

    title: ""

    Preview.InertialScroll {
        id: skinScroll
        objectName: "skinLibraryScroll"
        anchors.fill: parent
        contentHeight: skinColumn.implicitHeight
    Column {
        id: skinColumn
        width: skinScroll.width; spacing: 12
        Preview.MotionTabs {
            width: parent.width; visible: Theme.modern; labels: ["Skin", "Cape"]; currentIndex: skinPanel.tab === "skin" ? 0 : 1; namePrefix: "skinSection-"; onSelected: function(index) { skinPanel.tab = index === 0 ? "skin" : "cape"; }
        }
        Row {
            visible: !Theme.modern
            spacing: 18
            Repeater {
                model: [{ key: "skin", label: "Skin" }, { key: "cape", label: "Cape" }]
                Text {
                    text: modelData.label
                    color: skinPanel.tab === modelData.key ? Theme.accent : Theme.textMuted
                    font.pixelSize: Theme.fontHeading; font.bold: skinPanel.tab === modelData.key
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: skinPanel.tab = modelData.key }
                }
            }
        }
        Rectangle { width: parent.width; height: 1; color: Theme.border }
        Text {
            visible: skinPanel.hasShown && skinPanel.tab === "skin"
            width: parent.width; wrapMode: Text.WordWrap
            text: !skinPanel.hasShown ? ""
                  : skinPanel.shown.accountKind === "microsoft" ? Tr.phrase("Skin lấy từ hồ sơ Mojang. Bấm \"Thêm skin\" để upload file PNG lên Mojang — skin cũng được lưu vào thư viện bên dưới.")
                  : skinPanel.shown.accountKind === "ely" ? Tr.phrase("Skin lấy từ Ely.by. Bấm \"Thêm skin\" để upload PNG thẳng lên ely.by — bạn bè trong game thấy skin mới nhờ authlib-injector.")
                  : Tr.phrase("Tài khoản ngoại tuyến dùng skin mặc định (") + (skinPanel.shown.slim ? "Alex" : "Steve") + Tr.phrase("). Bấm \"Thêm skin\" để dùng file PNG riêng trong launcher.")
            color: Theme.textMuted; font.family: Theme.modern ? "Inter" : Theme.sans; font.pixelSize: Theme.fontBody; lineHeight: 1.3
        }
        Row {
            spacing: 8
            ActionButton {
                visible: skinPanel.hasShown && skinPanel.tab === "skin" && skinPanel.shown.accountKind !== "offline"
                primary: false
                label: Tr.phrase("⟳  Làm mới")
                onClicked: accountBridge.refreshSkins()
            }
        }
        SkinLibrary {
            width: parent.width
            visible: skinPanel.tab === "skin"
            shown: skinPanel.shown; hasShown: skinPanel.hasShown
            viewport: skinScroll
        }
        Text {
            id: uploadStatus
            visible: text !== ""
            color: uploadStatus.isError ? Theme.danger : Theme.accent
            font.family: Theme.modern ? "Inter" : Theme.sans; font.pixelSize: Theme.fontBody
            property bool isError: false
            Connections {
                target: accountBridge
                function onSkinUploaded(name) { uploadStatus.text = Tr.phrase("✓ Đã cập nhật skin cho ") + name; uploadStatus.isError = false; }
                function onSkinUploadFailed(msg) { uploadStatus.text = "✕ " + msg; uploadStatus.isError = true; }
            }
        }
        Column {
            width: parent.width; spacing: 12
            visible: skinPanel.hasShown && skinPanel.tab === "cape"
            /* Tải danh sách khi mở tab (và khi đổi tài khoản lúc tab đang mở) — không tải
               trước: đa số người chơi không có cape nào, đừng chạm mạng cho họ. */
            onVisibleChanged: if (visible) capeBridge.loadCapes(skinPanel.shown.accountId)
            Connections {
                target: skinPanel
                function onShownChanged() {
                    if (skinPanel.hasShown && skinPanel.tab === "cape")
                        capeBridge.loadCapes(skinPanel.shown.accountId)
                }
            }
            Text {
                width: parent.width; wrapMode: Text.WordWrap
                text: skinPanel.shown.accountKind === "microsoft"
                      ? Tr.phrase("Cape Mojang phát theo sự kiện — có cái nào thì chọn mặc ngay tại đây.")
                      : skinPanel.shown.accountKind === "ely"
                      ? Tr.phrase("Ely.by không có API cape — đổi tại ely.by, launcher sẽ hiện theo.")
                      : Tr.phrase("Tài khoản ngoại tuyến không có cape.")
                color: Theme.textMuted; font.family: Theme.modern ? "Inter" : Theme.sans; font.pixelSize: Theme.fontBody; lineHeight: 1.3
            }
            Flow {
                width: parent.width; spacing: 8
                Repeater {
                    model: capeBridge.loadedFor === skinPanel.shown.accountId ? capeBridge.capes : []
                    Rectangle {
                        required property var modelData
                        width: 92; height: 128; radius: Theme.radiusSmall
                        color: Theme.surfaceHigh
                        border.color: modelData.active ? Theme.accent : Theme.border
                        border.width: modelData.active ? 2 : 1
                        Column {
                            anchors.centerIn: parent; spacing: 6
                            Image {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 50; height: 80
                                source: modelData.textureUrl; sourceClipRect: Qt.rect(1, 1, 10, 16); smooth: false
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: modelData.active ? "✓ " + modelData.alias : modelData.alias
                                color: modelData.active ? Theme.accent : Theme.textMuted
                                font.pixelSize: Theme.fontLabel
                            }
                        }
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            /* Bấm cái đang mặc = gỡ cape (capeId rỗng), bấm cái khác = mặc nó. */
                            onClicked: capeBridge.applyCape(skinPanel.shown.accountId,
                                                           modelData.active ? "" : modelData.capeId)
                        }
                    }
                }
            }
            Row {
                spacing: 12
                Rectangle {
                    visible: skinPanel.shown.accountKind !== "microsoft" || capeBridge.capes.length === 0
                    width: 120; height: 100; radius: Theme.radiusSmall; color: Theme.surfaceHigh; border.color: Theme.border
                    Image {
                        visible: source != ""
                        anchors.centerIn: parent; width: 60; height: 96
                        /* `|| ""`: tài khoản chưa tải cape thì `capeFile` là undefined, mà
                           QUrl không nhận undefined — Qt kêu ra stderr mỗi lần vẽ. */
                        source: (skinPanel.hasShown && skinPanel.shown.capeFile) || ""
                        sourceClipRect: Qt.rect(1, 1, 10, 16); smooth: false
                    }
                    Text {
                        visible: !((skinPanel.hasShown && skinPanel.shown.capeFile) || "")
                        anchors.centerIn: parent; text: Tr.phrase("Không có cape"); color: Theme.textMuted; font.family: Theme.modern ? "Inter" : Theme.sans; font.pixelSize: Theme.fontBody
                    }
                }
            }
            Text {
                id: capeStatus
                visible: text !== ""
                color: capeStatus.isError ? Theme.danger : Theme.accent
                font.family: Theme.modern ? "Inter" : Theme.sans; font.pixelSize: Theme.fontBody
                property bool isError: false
                Connections {
                    target: capeBridge
                    function onCapeApplied(name) { capeStatus.text = Tr.phrase("✓ Đã đổi cape"); capeStatus.isError = false; }
                    function onCapeFailed(msg) { capeStatus.text = "✕ " + msg; capeStatus.isError = true; }
                }
            }
        }
    }
    }
}
