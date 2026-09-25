import QtQuick

/* Icon khối Minecraft xoay khi rê chuột.

   Vòng đời một lần rê: đứng yên -> tăng tốc dần đến trần -> rung kiểu "trứng sắp nở"
   -> rời chuột thì HÃM rồi quay ngược về đúng khung 0 (không nhảy cóc).

   Vì sao dải sprite chứ không xoay 3D thật: xoay khối thật cần shader, mà GL phần mềm
   (máy ảo, máy không có driver) không chạy shader. Đổi khung của một `Image` thì chạy
   mọi nơi và không tính gì lúc chạy.

   Chưa sinh xong dải thì hiện `glyph` chữ — mở launcher không phải chờ mấy cái icon. */
Item {
    id: root
    property string block: ""
    property string glyph: ""
    property color glyphColor: Theme.textMuted
    property bool spinning: false
    // `blockIcons ?` không thừa: lúc đóng cửa sổ, cầu nối chết trước cây QML và mọi ràng
    // buộc còn sống ném "property of null" ra stderr.
    readonly property string source: blockIcons ? (blockIcons.strips[root.block] || "") : ""
    readonly property bool ready: source.length > 0

    // Lộ ra cho test: khung hiện tại và tốc độ hiện tại.
    readonly property int frameCount: blockIcons ? blockIcons.frameCount : 1
    readonly property int frame: Math.floor(turn * frameCount) % frameCount
    property real turn: 0        // vị trí trong vòng, 0..1
    property real velocity: 0    // vòng/giây

    implicitWidth: 22; implicitHeight: 22

    readonly property real vmax: 1.1     // trần tốc độ, vòng/giây
    readonly property real ramp: 0.9     // gia tốc lên trần
    readonly property real brake: 1.6    // giảm tốc khi rời chuột
    readonly property real rewind: 1.3   // tốc độ quay ngược về khung 0
    readonly property real shake: 1.8    // biên rung (px) lúc chạm trần
    readonly property int throb: 620     // ms một nhịp trứng-sắp-nở

    Text {
        anchors.centerIn: parent
        visible: !root.ready
        text: root.glyph
        color: root.glyphColor
        font.pixelSize: 17
        Behavior on color { ColorAnimation { duration: Theme.quick } }
    }

    /* Cắt một khung khỏi dải ngang bằng cửa sổ `clip` + dịch `x`.

       KHÔNG dùng `sourceClipRect`: nó cắt ở tầng NẠP ảnh, nên mỗi lần đổi khung Qt giải mã
       lại cả dải. Đo được 8,9% một lõi cho MỘT khối đang xoay — bảy khối là 77%. Cách này
       nạp dải đúng một lần rồi chỉ dịch toạ độ: texture đã nằm trên GPU, đổi khung là đổi
       một con số. */
    Item {
        anchors.fill: parent
        visible: root.ready
        clip: true
        Image {
            id: sprite
            source: root.source
            // Dải rộng `frameCount` khung; kéo cho mỗi khung vừa đúng ô icon.
            width: root.width * root.frameCount
            height: root.height
            x: -root.frame * root.width
            fillMode: Image.Stretch
            smooth: true
            mipmap: true
            asynchronous: true
        }
    }

    /* Một đồng hồ duy nhất cho cả tốc độ lẫn rung. Chỉ chạy khi có việc: rê chuột, hoặc
       còn đang hãm/quay về. Đứng yên thì Timer tắt hẳn, không đốt CPU lúc rảnh. */
    property real elapsed: 0
    Timer {
        id: clock
        // 45fps: sprite nhảy theo bậc nên không cần 60, mà nhịp rung ngắn thì 30 thấy giật.
        interval: 1000 / 45
        repeat: true
        running: root.spinning || root.velocity > 0.001 || root.turn > 0.0005
        onTriggered: {
            var dt = interval / 1000;
            root.elapsed += interval;
            if (root.spinning) {
                root.velocity = Math.min(root.vmax, root.velocity + root.ramp * dt);
                root.turn = (root.turn + root.velocity * dt) % 1;
            } else if (root.velocity > 0.001) {
                // Hãm trước, quay về sau. Cắt thẳng về 0 lúc đang chạy nhanh trông như vỡ hình.
                root.velocity = Math.max(0, root.velocity - root.brake * dt);
                root.turn = (root.turn + root.velocity * dt) % 1;
            } else {
                // Đã đứng: đi đường NGẮN NHẤT về khung 0 — quá nửa vòng thì đi tiếp tới 1.
                root.velocity = 0;
                var step = root.rewind * dt;
                if (root.turn > 0.5) root.turn = root.turn + step >= 1 ? 0 : root.turn + step;
                else root.turn = Math.max(0, root.turn - step);
            }
        }
    }

    /* Rung kiểu "trứng sắp nở": phần lớn nhịp NẰM YÊN rồi một cơn giật ngắn phồng lên và
       tắt. Bao hình sin^2 trên 40% đầu mỗi nhịp lo đoạn phồng-tắt đó; rung đều tay thì
       trông như lỗi vẽ chứ không như sắp nở. Chỉ rung khi đã chạm trần. */
    readonly property real throbPhase: (elapsed % throb) / throb
    readonly property real throbEnvelope: throbPhase < 0.40
                                          ? Math.pow(Math.sin(throbPhase / 0.40 * Math.PI), 2) : 0
    readonly property real amplitude: (velocity > vmax * 0.92 ? shake * (velocity / vmax - 0.92) / 0.08 : 0)
                                      * throbEnvelope
    transform: [
        Translate {
            x: root.amplitude ? Math.sin(root.elapsed / 14) * root.amplitude : 0
            y: root.amplitude ? Math.cos(root.elapsed / 14 * 1.7) * root.amplitude * 0.7 : 0
        },
        Scale {
            origin.x: root.width / 2; origin.y: root.height / 2
            xScale: 1 + root.throbEnvelope * (root.amplitude ? 0.05 : 0)
            yScale: xScale
        }
    ]
}
