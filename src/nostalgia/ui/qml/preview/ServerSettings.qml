import QtQuick
import "../" as Legacy

InertialScroll {
    id: root
    objectName: "serverSettingsScroll"
    property bool writable: false
    property var values: ({})
    property bool eula: false
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
            PaymentText { id: status; width: parent.width; text: serverBridge.busy ? serverBridge.activity : serverBridge.note; color: serverBridge.busy ? GlassTheme.accent : GlassTheme.muted }
        }
        PaymentText { text: "THẾ GIỚI & KẾT NỐI"; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1; color: GlassTheme.muted }
        Grid { id: fields; width: parent.width; columns: width > 650 * GlassTheme.scale ? 2 : 1; spacing: 14
            Repeater {
                model: [{key: "motd", title: "Lời chào server"}, {key: "server-port", title: "Cổng kết nối · 1024–65535"},
                        {key: "max-players", title: "Số người chơi tối đa"}, {key: "spawn-protection", title: "Bảo vệ điểm hồi sinh · Block"},
                        {key: "view-distance", title: "Khoảng cách nhìn · Chunk"}, {key: "simulation-distance", title: "Khoảng cách mô phỏng · Chunk"}]
                Column { width: (fields.width - (fields.columns - 1) * fields.spacing) / fields.columns; spacing: 8
                    PaymentText { width: parent.width; text: modelData.title; font.weight: Font.DemiBold }
                    Input { objectName: "serverProperty-" + modelData.key; width: parent.width; enabled: root.writable; text: root.values[modelData.key] || ""; placeholder: modelData.title; onTextChanged: { if (text !== root.values[modelData.key]) root.updateValue(modelData.key, text); } }
                }
            }
        }
        Flow { width: parent.width; spacing: 14
            Column { width: Math.min(270 * GlassTheme.scale, form.width); spacing: 8
                PaymentText { text: "Chế độ chơi"; font.weight: Font.DemiBold }
                Select { objectName: "serverGameMode"; width: parent.width; model: ["survival", "creative", "adventure", "spectator"]; currentIndex: model.indexOf(root.values["gamemode"]); enabled: root.writable; onActivated: function(i) { root.updateValue("gamemode", model[i]); } }
            }
            Column { width: Math.min(270 * GlassTheme.scale, form.width); spacing: 8
                PaymentText { text: "Độ khó"; font.weight: Font.DemiBold }
                Select { objectName: "serverDifficulty"; width: parent.width; model: ["peaceful", "easy", "normal", "hard"]; currentIndex: model.indexOf(root.values["difficulty"]); enabled: root.writable; onActivated: function(i) { root.updateValue("difficulty", model[i]); } }
            }
        }
        Repeater {
            model: [{key: "pvp", title: "Cho phép PvP"}, {key: "white-list", title: "Chỉ cho người trong whitelist tham gia"}, {key: "online-mode", title: "Xác minh tài khoản Minecraft với Mojang"}]
            Row { spacing: 12; width: parent.width
                Legacy.Toggle { objectName: "serverToggle-" + modelData.key; enabled: root.writable; checked: root.values[modelData.key] === "true"; accessibleLabel: modelData.title; onToggled: function(value) { root.updateValue(modelData.key, value ? "true" : "false"); } }
                PaymentText { width: parent.width - 70; text: modelData.title; anchors.verticalCenter: parent.verticalCenter }
            }
        }
        PaymentText { width: parent.width; text: "Server chỉ nhận kết nối mạng của máy host. Chơi qua Internet cần địa chỉ/cổng được truy cập hoặc relay phù hợp. Console hỗ trợ whitelist add <tên người chơi>."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
        PaymentText { text: "JAVA & HIỆU NĂNG"; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
        PaymentText { text: "Bộ nhớ tối đa · MB"; font.weight: Font.DemiBold }
        Input { id: heap; objectName: "serverHeap"; width: parent.width; enabled: root.writable; placeholder: "2048 · Từ 512 đến 32768 MB" }
        PaymentText { text: "Java riêng · Để trống để dùng Java tự động"; color: GlassTheme.muted }
        Input { id: java; objectName: "serverJava"; width: parent.width; enabled: root.writable; placeholder: "Đường dẫn tới java hoặc java.exe" }
        Glass { width: parent.width; padding: 16; height: agreement.implicitHeight + 32
            Column { id: agreement; width: parent.width; spacing: 12
                PaymentText { width: parent.width; text: "Trước khi khởi chạy"; font.weight: Font.DemiBold }
                Row { width: parent.width; spacing: 12
                    Legacy.Toggle { objectName: "serverEula"; enabled: root.writable; checked: root.eula; accessibleLabel: "Đồng ý Minecraft EULA"; onToggled: function(value) { root.eula = value; } }
                    PaymentText { width: parent.width - 70; text: "Tôi đã đọc và đồng ý Minecraft EULA."; anchors.verticalCenter: parent.verticalCenter }
                }
                Button { label: "Đọc Minecraft EULA ↗"; quiet: true; onClicked: Qt.openUrlExternally("https://www.minecraft.net/eula") }
                PaymentText { width: parent.width; text: "Lưu cấu hình trước khi khởi chạy. Plugin/mod và cấu hình chỉ được đổi khi server đã dừng."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
            }
        }
    }
}
