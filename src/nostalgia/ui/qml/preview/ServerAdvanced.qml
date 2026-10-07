import QtQuick
import QtQuick.Controls as Controls

InertialScroll {
    id: root
    objectName: "serverAdvancedScroll"
    property bool writable: false
    property string serverId: ""
    property string fileName: ""
    signal trashRequested
    contentHeight: body.implicitHeight + 12
    Connections { target: serverBridge; function onConfigLoaded() { editor.text = serverBridge.configText; } function onSelectionLoaded() { root.fileName = ""; editor.text = ""; } }
    Column { id: body; width: parent.width - 8; spacing: 16
        PaymentText { width: parent.width; text: "Cấu hình nâng cao"; font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold }
        PaymentText { width: parent.width; text: "Sửa file YAML/TOML/JSON/properties của nền tảng hoặc plugin. Giữ đúng cú pháp của file; cấu hình chỉ có hiệu lực sau khi khởi chạy lại."; color: GlassTheme.muted }
        Row { width: parent.width; spacing: 10
            Select { objectName: "serverConfigFile"; width: Math.max(140, parent.width - read.width - 10); model: serverBridge.configFiles; currentIndex: -1; displayText: root.fileName || "Chọn file cấu hình…"; enabled: !serverBridge.busy; onActivated: function(i) { root.fileName = serverBridge.configFiles[i]; serverBridge.readConfig(root.fileName); } }
            Button { id: read; label: "Đọc lại"; clickable: !!root.fileName && !serverBridge.busy; onClicked: { editor.focus = false; serverBridge.readConfig(root.fileName); } }
        }
        Rectangle { width: parent.width; height: 240 * GlassTheme.scale; radius: 14; color: GlassTheme.inputSurface; border.color: GlassTheme.stroke
            Controls.ScrollView { anchors.fill: parent; anchors.margins: 12
                Controls.TextArea { id: editor; objectName: "serverConfigEditor"; readOnly: !root.writable; text: serverBridge.configText; color: GlassTheme.text; font.family: GlassTheme.font; font.pixelSize: GlassTheme.fontCaption; selectByMouse: true; wrapMode: TextEdit.NoWrap; background: null }
            }
        }
        Button { objectName: "serverConfigSave"; label: "Lưu file cấu hình"; primary: true; clickable: root.writable && !!root.fileName; onClicked: serverBridge.saveConfig(root.fileName, editor.text) }
        PaymentText { width: parent.width; text: serverBridge.note; color: GlassTheme.muted }
        Glass { width: parent.width; padding: 16; height: removal.implicitHeight + 32
            Column { id: removal; width: parent.width; spacing: 12
                PaymentText { text: "Lưu trữ server"; font.weight: Font.DemiBold }
                PaymentText { width: parent.width; text: "Chuyển cả thư mục server vào servers/.trash. Thế giới và nội dung được giữ lại để bạn có thể lấy lại bằng cách mở thư mục dữ liệu."; color: GlassTheme.muted }
                Button { objectName: "serverTrash"; label: "Chuyển vào thùng rác"; clickable: root.writable; quiet: true; onClicked: { var serverId = root.serverId; confirmDialog.ask("Chuyển server vào thùng rác?", "Toàn bộ thế giới, plugin và mod được giữ trong servers/.trash.", function() { serverBridge.trash(serverId); root.trashRequested(); }); } }
            }
        }
    }
}
