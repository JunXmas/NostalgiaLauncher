import QtQuick
import "../" as Legacy

/* Slide Nos Client đầu băng trượt trang chủ: chữ + lưới tính năng có icon bên trái, chồng ảnh chụp
   thật (lời nhạc trên trời, hub, cosmetic) xoay vòng bên phải. Icon cắt từ atlas trong mod, ảnh
   chụp từ game thật — không vẽ minh hoạ thay cho thứ người chơi sẽ thấy.
   Nút chính bật Nos Client cho bản chơi đang chọn (cùng công tắc với NosChip); bản chơi không
   hỗ trợ thì mời tạo bản Fabric 1.21.11. */
Item {
    id: root
    objectName: "nosShowcase"
    property var chosen: null
    property bool active: true
    property int textInset: 32
    readonly property bool narrow: width < 860
    readonly property real contentHeight: copy.implicitHeight
    readonly property bool supported: !!root.chosen && root.chosen.nosClientSupported === true
    readonly property bool nosOn: root.supported && root.chosen.nosClientEnabled === true
    readonly property bool locked: bridge.gameRunning || bridge.busy
    signal createRequested
    signal cosmeticRequested

    readonly property var features: [
        { icon: "lyrics", title: Legacy.Tr.phrase("Lời nhạc trên trời"), note: Legacy.Tr.phrase("Spotify, bụi sao, karaoke") },
        { icon: "minimap", title: Legacy.Tr.phrase("Minimap & bản đồ"), note: Legacy.Tr.phrase("Riêng cho từng world") },
        { icon: "waypoint", title: Legacy.Tr.phrase("Waypoint"), note: Legacy.Tr.phrase("Đánh dấu, chiếu trên HUD") },
        { icon: "fps", title: Legacy.Tr.phrase("HUD kính"), note: Legacy.Tr.phrase("FPS, toạ độ, keystroke") },
        { icon: "zoom", title: Legacy.Tr.phrase("Zoom & freelook"), note: Legacy.Tr.phrase("Lăn chuột đổi mức") },
        { icon: "look", title: Legacy.Tr.phrase("Cosmetic 3D"), note: Legacy.Tr.phrase("Cánh, cape, đai đầu") }
    ]
    readonly property var shots: [
        { source: "../assets/nos/shot-lyrics.jpg", caption: Legacy.Tr.phrase("Lời nhạc ngưng tụ từ bụi sao, bị núi che") },
        { source: "../assets/nos/shot-hub.jpg", caption: Legacy.Tr.phrase("Cài đặt R-Shift: vòng danh mục, kính có chiều sâu") },
        { source: "../assets/nos/shot-angel.jpg", caption: Legacy.Tr.phrase("Seraph Angel — mặc thử ngay trong game") },
        { source: "../assets/nos/shot-crimson.jpg", caption: Legacy.Tr.phrase("Crimson Oath — cánh quỷ có animation") }
    ]
    property int shot: 0
    property real enter: 0
    onActiveChanged: if (active) entrance.restart()
    Component.onCompleted: if (active) entrance.restart()
    NumberAnimation { id: entrance; target: root; property: "enter"; from: 0; to: 1; duration: GlassTheme.reducedMotion ? 0 : 900; easing.type: Easing.OutCubic }

    function primaryAction() {
        if (!root.supported) root.createRequested();
        else if (!root.nosOn) bridge.toggleNosClient(root.chosen.instanceId, true);
        else bridge.play(root.chosen.instanceId);
    }

    Timer {
        interval: 4200; repeat: true
        running: root.active && root.visible && !GlassTheme.reducedMotion
        onTriggered: root.shot = (root.shot + 1) % root.shots.length
    }

    // Nền: vầng sáng accent loang từ góc ảnh, để slide có chiều sâu thay vì mảng phẳng.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#0d1412" }
            GradientStop { position: 0.6; color: "#111c18" }
            GradientStop { position: 1.0; color: "#152520" }
        }
    }
    Image {
        // Vầng sáng mềm sau chồng ảnh (cùng ảnh glow các trang khác dùng).
        source: "../assets/glow.png"
        width: root.height * 1.5; height: width
        x: root.width * 0.74 - width / 2; y: root.height * 0.45 - height / 2
        opacity: 0.32 * root.enter
        smooth: true
    }
    Repeater {
        // Vài đốm sao trôi chậm — cùng tinh thần lời nhạc bụi sao trong game.
        model: 14
        Rectangle {
            readonly property real seed: (index * 0.61803) % 1
            width: 2 + (index % 3); height: width; radius: width / 2
            color: index % 4 === 0 ? GlassTheme.accent : "#d8f0e2"
            x: root.width * (0.45 + 0.55 * ((index * 0.381966) % 1))
            y: root.height * seed + Math.sin(twinkle.t + index) * 6
            opacity: (0.25 + 0.5 * (0.5 + 0.5 * Math.sin(twinkle.t * (0.8 + seed) + index * 1.7))) * root.enter
        }
    }
    QtObject {
        id: twinkle
        property real t: 0
        NumberAnimation on t { from: 0; to: Math.PI * 2; duration: 9000; loops: Animation.Infinite; running: root.active && root.visible && !GlassTheme.reducedMotion }
    }

    // ----- trái: chữ, lưới tính năng, nút -----
    Column {
        id: copy
        anchors { left: parent.left; leftMargin: root.textInset; verticalCenter: parent.verticalCenter }
        width: root.narrow ? parent.width - root.textInset * 2 : Math.min(470, parent.width * 0.47)
        spacing: 14
        opacity: root.enter
        transform: Translate { y: 14 * (1 - root.enter) }

        Row {
            spacing: 8
            Image { source: "../assets/nos/icon-sky.png"; width: 18; height: 18; smooth: true; mipmap: true; anchors.verticalCenter: parent.verticalCenter }
            PaymentText {
                anchors.verticalCenter: parent.verticalCenter
                text: Legacy.Tr.phrase("MỚI · NOS CLIENT 0.2")
                color: GlassTheme.accent
                font.pixelSize: GlassTheme.fontCaption
                font.letterSpacing: 1.4
            }
        }
        PaymentText {
            width: parent.width
            text: Legacy.Tr.phrase("Minecraft của bạn,\nđẹp hơn một bậc.")
            font.pixelSize: (root.narrow ? 26 : 34) * GlassTheme.scale
            font.weight: Font.DemiBold
            font.letterSpacing: -0.8
            lineHeight: 1.1
        }
        Grid {
            id: grid
            width: parent.width
            columns: 2
            columnSpacing: 10; rowSpacing: 8
            Repeater {
                model: root.features
                Rectangle {
                    id: feature
                    width: (grid.width - grid.columnSpacing) / 2
                    height: 46
                    radius: 12
                    color: featureHover.hovered ? GlassTheme.alpha(GlassTheme.brand, 0.16) : "#14ffffff"
                    border.color: featureHover.hovered ? GlassTheme.alpha(GlassTheme.accent, 0.55) : "#1cffffff"
                    Behavior on color { ColorAnimation { duration: GlassTheme.quick } }
                    // Vào so le từng ô theo thứ tự đọc.
                    opacity: Math.max(0, Math.min(1, root.enter * 2.2 - index * 0.16))
                    transform: Translate { x: 10 * (1 - feature.opacity) }
                    HoverHandler { id: featureHover }
                    Rectangle {
                        id: iconTile
                        anchors { left: parent.left; leftMargin: 7; verticalCenter: parent.verticalCenter }
                        width: 32; height: 32; radius: 9
                        color: GlassTheme.alpha(GlassTheme.brand, 0.22)
                        Image {
                            anchors.centerIn: parent
                            source: "../assets/nos/icon-" + modelData.icon + ".png"
                            width: 26; height: 26; smooth: true; mipmap: true
                            scale: featureHover.hovered ? 1.08 : 1
                            Behavior on scale { NumberAnimation { duration: GlassTheme.quick; easing.type: Easing.OutBack } }
                        }
                    }
                    Column {
                        anchors { left: iconTile.right; leftMargin: 9; right: parent.right; rightMargin: 8; verticalCenter: parent.verticalCenter }
                        spacing: 1
                        PaymentText { width: parent.width; text: modelData.title; font.pixelSize: GlassTheme.fontLabel; font.weight: Font.DemiBold; elide: Text.ElideRight }
                        PaymentText { width: parent.width; text: modelData.note; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote; elide: Text.ElideRight }
                    }
                }
            }
        }
        Flow {
            width: parent.width
            spacing: 10
            Button {
                objectName: "nosShowcaseAction"
                height: 46
                primary: true
                label: !root.supported ? Legacy.Tr.phrase("Tạo bản Fabric 1.21.11  +")
                     : !root.nosOn ? Legacy.Tr.phrase("Bật Nos Client")
                     : bridge.gameRunning ? Legacy.Tr.phrase("Đang chơi") : Legacy.Tr.phrase("Chơi với Nos  →")
                clickable: !root.supported || (!root.locked && (!root.nosOn || bridge.activePlayerName.length > 0))
                onClicked: root.primaryAction()
            }
            Button {
                height: 46
                quiet: true
                label: Legacy.Tr.phrase("Xem cosmetic")
                onClicked: root.cosmeticRequested()
            }
        }
        PaymentText {
            objectName: "nosShowcaseHint"
            width: parent.width
            wrapMode: Text.WordWrap
            color: GlassTheme.muted
            font.pixelSize: GlassTheme.fontNote
            text: !root.supported ? Legacy.Tr.phrase("Nos Client chạy trên bản chơi Fabric 1.21.11. Launcher tự tải và cập nhật.")
                : root.locked && !root.nosOn ? Legacy.Tr.phrase("Đóng Minecraft để bật Nos Client.")
                : root.nosOn ? Legacy.Tr.phrase("Đang bật cho ") + root.chosen.label + Legacy.Tr.phrase(". Trong game bấm R-Shift để mở cài đặt.")
                : Legacy.Tr.phrase("Bật cho ") + root.chosen.label + Legacy.Tr.phrase(" — một chạm, lần chơi sau là có.")
        }
    }

    // ----- phải: chồng ảnh chụp thật, xoay vòng -----
    Item {
        id: gallery
        visible: !root.narrow
        anchors { right: parent.right; rightMargin: root.textInset + 30; verticalCenter: parent.verticalCenter }
        width: Math.min(parent.width - copy.width - root.textInset * 2 - 60, 450)
        height: width * 0.62
        opacity: root.enter
        transform: Translate { x: 30 * (1 - root.enter) }

        Repeater {
            model: root.shots
            Item {
                id: card
                // Vị trí trong chồng: 0 = trước nhất. Ảnh sau lệch lên phải, nhỏ dần, mờ dần.
                readonly property int depth: (index - root.shot + root.shots.length) % root.shots.length
                width: gallery.width; height: gallery.height
                z: root.shots.length - depth
                x: depth * 18
                y: -depth * 14
                scale: 1 - depth * 0.06
                opacity: depth > 2 ? 0 : 1 - depth * 0.28
                transformOrigin: Item.TopRight
                Behavior on x { NumberAnimation { duration: GlassTheme.slow; easing.type: Easing.OutCubic } }
                Behavior on y { NumberAnimation { duration: GlassTheme.slow; easing.type: Easing.OutCubic } }
                Behavior on scale { NumberAnimation { duration: GlassTheme.slow; easing.type: Easing.OutCubic } }
                Behavior on opacity { NumberAnimation { duration: GlassTheme.slow } }

                // Bóng đổ mềm giả lập bằng hai lớp viền tối lệch xuống.
                Rectangle { anchors.fill: parent; anchors.topMargin: 10; anchors.margins: -2; radius: 18; color: "#40000000" }
                Rectangle {
                    id: frame
                    anchors.fill: parent
                    radius: 16
                    color: "#0b100e"
                    border.color: card.depth === 0 ? GlassTheme.alpha(GlassTheme.accent, 0.45) : "#26ffffff"
                    clip: true
                    Image {
                        anchors.fill: parent
                        anchors.margins: 1
                        source: modelData.source
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        smooth: true; mipmap: true
                        // Ảnh trước nhất trôi chậm (Ken Burns) cho có nhịp sống.
                        scale: card.depth === 0 && root.active ? 1.06 : 1.0
                        Behavior on scale { NumberAnimation { duration: 4200; easing.type: Easing.InOutSine } }
                    }
                    Rectangle {
                        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                        height: 54
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#000b100e" }
                            GradientStop { position: 1.0; color: "#e60b100e" }
                        }
                        visible: card.depth === 0
                        PaymentText {
                            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 12 }
                            text: modelData.caption
                            font.pixelSize: GlassTheme.fontNote
                            color: "#e8f2ec"
                            elide: Text.ElideRight
                        }
                    }
                }
                TapHandler { enabled: card.depth !== 0; onTapped: root.shot = index }
            }
        }
        Row {
            anchors { horizontalCenter: parent.horizontalCenter; top: parent.bottom; topMargin: 14 }
            spacing: 6
            Repeater {
                model: root.shots.length
                Rectangle {
                    width: index === root.shot ? 16 : 6; height: 6; radius: 3
                    color: index === root.shot ? GlassTheme.accent : "#55ffffff"
                    Behavior on width { NumberAnimation { duration: GlassTheme.quick } }
                    TapHandler { onTapped: root.shot = index }
                }
            }
        }
    }
}
