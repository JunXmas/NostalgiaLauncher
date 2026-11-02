import QtQuick
import "../" as Legacy

/* Slide server Forgotten Worlds: ảnh cảnh server (từ replay) chạy nền, chữ + nút đè lên.
   Chưa có bản chơi FW: mời tạo. Đã có: VÀO SERVER thẳng; modpack mới: CẬP NHẬT. */
Item {
    id: root
    objectName: "serverShowcase"
    readonly property string address: "snow.pikamc.vn:25079"
    readonly property var pack: (bridge.instances || []).find(function (i) {
        return i.modpackPreset === "forgotten-worlds";
    }) || null
    readonly property bool updateReady: root.pack !== null && root.pack.modpackUpdateAvailable === true
    readonly property var shots: ["../assets/server/fw-1.jpg", "../assets/server/fw-2.jpg",
                                  "../assets/server/fw-3.jpg", "../assets/server/fw-4.jpg"]
    property int shot: 0
    property bool active: true
    property int textInset: 32
    readonly property real contentHeight: info.implicitHeight
    signal createRequested

    Timer {
        interval: 5000; repeat: true; running: root.active && root.visible
        onTriggered: root.shot = (root.shot + 1) % root.shots.length
    }
    Repeater {
        model: root.shots
        Image {
            anchors.fill: parent
            source: modelData
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            smooth: true; mipmap: true
            opacity: index === root.shot ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: GlassTheme.reducedMotion ? 0 : 700 } }
        }
    }
    // Tối dần sang trái để chữ đọc được trên mọi ảnh.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#e60b100d" }
            GradientStop { position: 0.55; color: "#800b100d" }
            GradientStop { position: 1.0; color: "#100b100d" }
        }
    }
    Column {
        id: info
        anchors.left: parent.left
        anchors.leftMargin: root.textInset
        anchors.verticalCenter: parent.verticalCenter
        width: Math.min(520, parent.width - root.textInset * 2)
        spacing: 14
        PaymentText {
            text: Legacy.Tr.phrase("SERVER CỦA CỘNG ĐỒNG")
            color: GlassTheme.accent
            font.pixelSize: GlassTheme.fontCaption
            font.letterSpacing: 1.2
        }
        PaymentText {
            width: parent.width
            text: "Forgotten Worlds"
            font.pixelSize: GlassTheme.fontPrice
            font.weight: Font.DemiBold
            font.letterSpacing: -1
        }
        PaymentText {
            width: parent.width
            text: Legacy.Tr.phrase("Sinh tồn công nghiệp với Create, sinh vật Naturalist, chiếm lãnh thổ buổi tối. Minecraft 1.21.11, Việt hoá sẵn.")
            color: "#dfe6dc"
            font.pixelSize: GlassTheme.fontBody
        }
        PaymentText {
            objectName: "serverShowcaseStatus"
            width: parent.width
            text: root.pack === null ? root.address
                : root.updateReady ? Legacy.Tr.phrase("Có modpack mới ") + root.pack.modpackLatestVersion + Legacy.Tr.phrase(" (đang dùng ") + root.pack.modpackVersion + ")"
                : Legacy.Tr.phrase("Modpack ") + root.pack.modpackVersion + " · " + root.address
            color: root.updateReady ? GlassTheme.accent : "#b8c2b4"
            font.pixelSize: GlassTheme.fontCaption
        }
        Button {
            objectName: "serverShowcaseAction"
            height: 46
            primary: true
            label: root.pack === null ? Legacy.Tr.phrase("Tạo bản chơi server  +")
                 : root.updateReady ? Legacy.Tr.phrase("Cập nhật modpack")
                 : bridge.gameRunning ? Legacy.Tr.phrase("Đang chơi") : Legacy.Tr.phrase("Vào server  →")
            clickable: root.pack === null || (!bridge.gameRunning && !bridge.busy && !bridge.storageBusy
                       && (root.updateReady || bridge.activePlayerName.length > 0))
            onClicked: {
                if (root.pack === null) root.createRequested();
                else if (root.updateReady) bridge.updateModpack(root.pack.instanceId);
                else bridge.playServer(root.pack.instanceId, root.address);
            }
        }
    }
}
