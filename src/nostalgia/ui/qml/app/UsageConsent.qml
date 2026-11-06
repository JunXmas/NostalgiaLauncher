import QtQuick
import QtQuick.Window
import QtQuick.Controls as Controls
import "../" as Legacy

Item {
    id: coordinator
    property bool eligible: false
    Timer {
        interval: 1500
        repeat: true
        running: usageBridge.available && usageBridge.choice === "unselected"
        onTriggered: {
            if (coordinator.eligible && coordinator.Window.window && coordinator.Window.window.active
                && !choice.opened && choice.parent && choice.parent.visibleChildren.length === 0)
                choice.open();
        }
    }
    Connections {
        target: usageBridge
        function onChanged() { if (usageBridge.choice !== "unselected") choice.close(); }
    }
    WorkspaceDialog {
        id: choice
        objectName: "usageConsentDialog"
        title: Legacy.Tr.phrase("Giúp cải thiện Nostalgia")
        description: Legacy.Tr.phrase("Bạn có muốn chia sẻ thống kê sử dụng cơ bản để giúp chúng tôi cải thiện launcher?")
        preferredWidth: 620 * GlassTheme.scale
        preferredHeight: 440 * GlassTheme.scale
        onOpened: decline.forceActiveFocus()
        onClosed: { if (usageBridge.choice === "unselected") usageBridge.choose(false); }
        InertialScroll {
            objectName: "usageConsentBody"
            anchors.fill: parent
            contentHeight: contents.implicitHeight
            Column {
                id: contents
                width: parent.width
                spacing: 14
                UsagePurpose {}
                PaymentText { width: parent.width; text: Legacy.Tr.phrase("Khi bạn đồng ý chia sẻ, launcher đếm bản cài hoạt động/ngày. Dữ liệu gồm ngày UTC, phiên bản launcher, nhóm hệ điều hành và mã ngẫu nhiên theo ngày."); color: GlassTheme.muted }
                PaymentText { width: parent.width; text: Legacy.Tr.phrase("Không gửi tên tài khoản, nội dung chat hay mã nhận diện phần cứng. Bạn có thể thay đổi lựa chọn trong Cài đặt."); color: GlassTheme.muted }
                Button { objectName: "consentViewPayload"; label: Legacy.Tr.phrase("Xem dữ liệu được gửi"); quiet: true; onClicked: usageBridge.showPayload() }
                Button { label: Legacy.Tr.phrase("Thông tin quyền riêng tư"); quiet: true; onClicked: usageBridge.showPayload() }
            }
        }
        footer: Flow {
            width: choice.bodyWidth
            spacing: 12
            Button { id: decline; objectName: "usageDecline"; width: (parent.width - 12) / 2; label: Legacy.Tr.phrase("Không gửi"); onClicked: usageBridge.choose(false) }
            Button { objectName: "usageAccept"; width: (parent.width - 12) / 2; label: Legacy.Tr.phrase("Đồng ý chia sẻ"); onClicked: usageBridge.choose(true) }
        }
    }
}
