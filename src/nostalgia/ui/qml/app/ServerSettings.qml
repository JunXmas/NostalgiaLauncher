import QtQuick
import "../" as Legacy

InertialScroll {
    id: root
    objectName: "serverSettingsScroll"
    property bool writable: false
    property var values: ({})
    property bool eula: false
    readonly property var gameModes: ["survival", "creative", "adventure", "spectator"]
    readonly property var difficulties: ["peaceful", "easy", "normal", "hard"]
    function populate() {
        values = serverBridge.selected.properties || ({});
        heap.text = String(serverBridge.selected.heap_megabytes || 2048);
        java.text = serverBridge.selected.java_binary || "";
        eula = serverBridge.selected.eula === true;
    }
    function updateValue(propertyKey, value) {
        var next = Object.assign({}, root.values); next[propertyKey] = value; root.values = next;
    }
    function save() { serverBridge.saveSettings(root.values, parseInt(heap.text) || 0, java.text, root.eula); }
    contentHeight: form.implicitHeight + 10
    Connections { target: serverBridge; function onSelectionLoaded() { root.populate(); } }
    Column { id: form; width: parent.width - 8; spacing: 18
        Glass { width: parent.width; padding: 14; height: status.implicitHeight + 28
            PaymentText { id: status; width: parent.width; text: serverBridge.busy ? Legacy.Tr.message(serverBridge.activity) : Legacy.Tr.message(serverBridge.note); color: serverBridge.busy ? GlassTheme.accent : GlassTheme.muted }
        }
        PaymentText { text: Legacy.Tr.phrase("THẾ GIỚI & KẾT NỐI"); font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1; color: GlassTheme.muted }
        Grid { id: fields; width: parent.width; columns: width > 650 * GlassTheme.scale ? 2 : 1; spacing: 14
            Repeater {
                model: [{key: "motd", title: Legacy.Tr.phrase("Lời chào server")}, {key: "server-port", title: Legacy.Tr.phrase("Cổng kết nối · 1024–65535")},
                        {key: "max-players", title: Legacy.Tr.phrase("Số người chơi tối đa")}, {key: "spawn-protection", title: Legacy.Tr.phrase("Bảo vệ điểm hồi sinh · Block")},
                        {key: "view-distance", title: Legacy.Tr.phrase("Khoảng cách nhìn · Chunk")}, {key: "simulation-distance", title: Legacy.Tr.phrase("Khoảng cách mô phỏng · Chunk")}]
                Column { width: (fields.width - (fields.columns - 1) * fields.spacing) / fields.columns; spacing: 8
                    PaymentText { width: parent.width; text: modelData.title; font.weight: Font.DemiBold }
                    Input { objectName: "serverProperty-" + modelData.key; width: parent.width; enabled: root.writable; text: root.values[modelData.key] || ""; placeholder: modelData.title; onTextChanged: { if (text !== root.values[modelData.key]) root.updateValue(modelData.key, text); } }
                }
            }
        }
        Flow { width: parent.width; spacing: 14
            Column { width: Math.min(270 * GlassTheme.scale, form.width); spacing: 8
                PaymentText { text: Legacy.Tr.phrase("Chế độ chơi"); font.weight: Font.DemiBold }
                Select { objectName: "serverGameMode"; width: parent.width; model: [Legacy.Tr.phrase("Sinh tồn"), Legacy.Tr.phrase("Sáng tạo"), Legacy.Tr.phrase("Phiêu lưu"), Legacy.Tr.phrase("Khán giả")]; currentIndex: root.gameModes.indexOf(root.values["gamemode"]); enabled: root.writable; onActivated: function(i) { root.updateValue("gamemode", root.gameModes[i]); } }
            }
            Column { width: Math.min(270 * GlassTheme.scale, form.width); spacing: 8
                PaymentText { text: Legacy.Tr.phrase("Độ khó"); font.weight: Font.DemiBold }
                Select { objectName: "serverDifficulty"; width: parent.width; model: [Legacy.Tr.phrase("Yên bình"), Legacy.Tr.phrase("Dễ"), Legacy.Tr.phrase("Bình thường"), Legacy.Tr.phrase("Khó")]; currentIndex: root.difficulties.indexOf(root.values["difficulty"]); enabled: root.writable; onActivated: function(i) { root.updateValue("difficulty", root.difficulties[i]); } }
            }
        }
        Repeater {
            model: [{key: "pvp", title: Legacy.Tr.phrase("Cho phép PvP")}, {key: "white-list", title: Legacy.Tr.phrase("Chỉ cho người trong whitelist tham gia")}, {key: "online-mode", title: Legacy.Tr.phrase("Xác minh tài khoản Minecraft với Mojang")}]
            Row { spacing: 12; width: parent.width
                Legacy.Toggle { objectName: "serverToggle-" + modelData.key; enabled: root.writable; checked: root.values[modelData.key] === "true"; accessibleLabel: modelData.title; onToggled: function(value) { root.updateValue(modelData.key, value ? "true" : "false"); } }
                PaymentText { width: parent.width - 70; text: modelData.title; anchors.verticalCenter: parent.verticalCenter }
            }
        }
        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Server chỉ nhận kết nối mạng của máy host. Chơi qua Internet cần địa chỉ/cổng được truy cập hoặc relay phù hợp. Console hỗ trợ whitelist add <tên người chơi>."); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
        PaymentText { text: Legacy.Tr.phrase("JAVA & HIỆU NĂNG"); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
        PaymentText { text: Legacy.Tr.phrase("Bộ nhớ tối đa · MB"); font.weight: Font.DemiBold }
        Input { id: heap; objectName: "serverHeap"; width: parent.width; enabled: root.writable; placeholder: Legacy.Tr.phrase("2048 · Từ 512 đến 32768 MB") }
        PaymentText { text: Legacy.Tr.phrase("Java riêng · Để trống để dùng Java tự động"); color: GlassTheme.muted }
        Input { id: java; objectName: "serverJava"; width: parent.width; enabled: root.writable; placeholder: Legacy.Tr.phrase("Đường dẫn tới java hoặc java.exe") }
        Glass { width: parent.width; padding: 16; height: agreement.implicitHeight + 32
            Column { id: agreement; width: parent.width; spacing: 12
                PaymentText { width: parent.width; text: Legacy.Tr.phrase("Trước khi khởi chạy"); font.weight: Font.DemiBold }
                Row { width: parent.width; spacing: 12
                    Legacy.Toggle { objectName: "serverEula"; enabled: root.writable; checked: root.eula; accessibleLabel: Legacy.Tr.phrase("Đồng ý Minecraft EULA"); onToggled: function(value) { root.eula = value; } }
                    PaymentText { width: parent.width - 70; text: Legacy.Tr.phrase("Tôi đã đọc và đồng ý Minecraft EULA."); anchors.verticalCenter: parent.verticalCenter }
                }
                Button { label: Legacy.Tr.phrase("Đọc Minecraft EULA ↗"); quiet: true; onClicked: Qt.openUrlExternally("https://www.minecraft.net/eula") }
                PaymentText { width: parent.width; text: Legacy.Tr.phrase("Lưu cấu hình trước khi khởi chạy. Plugin/mod và cấu hình chỉ được đổi khi server đã dừng."); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
            }
        }
    }
}
