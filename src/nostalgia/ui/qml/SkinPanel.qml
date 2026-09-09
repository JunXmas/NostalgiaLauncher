import QtQuick

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

    Column {
        anchors.fill: parent; spacing: 12
        Row {
            spacing: 18
            Repeater {
                model: [{ key: "skin", label: "Skin" }, { key: "cape", label: "Cape" }]
                Text {
                    text: modelData.label
                    color: skinPanel.tab === modelData.key ? Theme.accent : Theme.textMuted
                    font.pixelSize: 13; font.bold: skinPanel.tab === modelData.key
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: skinPanel.tab = modelData.key }
                }
            }
        }
        Rectangle { width: parent.width; height: 1; color: Theme.border }
        Text {
            visible: skinPanel.hasShown && skinPanel.tab === "skin"
            width: parent.width; wrapMode: Text.WordWrap
            text: !skinPanel.hasShown ? ""
                  : skinPanel.shown.accountKind === "microsoft" ? "Skin lấy từ hồ sơ Mojang. Bấm \"Thêm skin\" để upload file PNG lên Mojang — skin cũng được lưu vào thư viện bên dưới."
                  : skinPanel.shown.accountKind === "ely" ? "Skin lấy từ Ely.by. Đổi skin/cape thật tại ely.by → Skins (bạn bè trong game thấy nhờ authlib-injector); \"Thêm skin\" chỉ đổi ảnh hiện trong launcher."
                  : "Tài khoản ngoại tuyến dùng skin mặc định (" + (skinPanel.shown.slim ? "Alex" : "Steve") + "). Bấm \"Thêm skin\" để dùng file PNG riêng trong launcher."
            color: Theme.textMuted; font.pixelSize: 12; lineHeight: 1.3
        }
        ActionButton {
            visible: skinPanel.hasShown && skinPanel.tab === "skin" && skinPanel.shown.accountKind !== "offline"
            primary: false
            label: "⟳  Làm mới"
            onClicked: accountBridge.refreshSkins()
        }
        SkinLibrary {
            width: parent.width
            visible: skinPanel.tab === "skin"
            shown: skinPanel.shown; hasShown: skinPanel.hasShown
        }
        Text {
            id: uploadStatus
            visible: text !== ""
            color: uploadStatus.isError ? Theme.danger : Theme.accent
            font.pixelSize: 11
            property bool isError: false
            Connections {
                target: accountBridge
                function onSkinUploaded(name) { uploadStatus.text = "✓ Đã cập nhật skin cho " + name; uploadStatus.isError = false; }
                function onSkinUploadFailed(msg) { uploadStatus.text = "✕ " + msg; uploadStatus.isError = true; }
            }
        }
        Row {
            visible: skinPanel.hasShown && skinPanel.tab === "cape"; spacing: 12
            Rectangle {
                width: 120; height: 100; radius: Theme.radiusSmall; color: Theme.surfaceHigh; border.color: Theme.border
                Image {
                    visible: skinPanel.hasShown && skinPanel.shown.capeFile !== ""
                    anchors.centerIn: parent; width: 60; height: 96
                    source: skinPanel.hasShown ? skinPanel.shown.capeFile : ""; sourceClipRect: Qt.rect(1, 1, 10, 16); smooth: false
                }
                Text {
                    visible: !(skinPanel.hasShown && skinPanel.shown.capeFile !== "")
                    anchors.centerIn: parent; text: "Không có cape"; color: Theme.textMuted; font.pixelSize: 11
                }
            }
        }
    }
}
