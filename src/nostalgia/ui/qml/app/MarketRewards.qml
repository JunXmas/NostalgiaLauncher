import QtQuick
import "../" as Legacy
Glass { padding: 0;
    id: root; objectName: "marketRewardCard"
    property var rewards: ({})
    property bool marketEnabled: false
    height: content.implicitHeight+32
    function date(value) { return value ? new Date(value*1000).toLocaleString(Qt.locale(Legacy.Tr.localeName)) : ""; }
    Column {
        id: content; x: 16; y: 16; width: parent.width-32; spacing: 12
        PaymentText { width: parent.width; text: "Nostalgia+ · "+Legacy.Tr.phrase("Điểm thưởng ngày"); font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold; wrapMode: Text.WordWrap }
        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Điểm thưởng")+": "+(root.rewards.balance||0); color: GlassTheme.accent }
        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Chỉ Nostalgia+ còn hiệu lực, gồm gói năm và lifetime, được nhận và dùng điểm. Điểm tách khỏi coin nạp; 1 điểm giảm 1 coin, chỉ giảm một phần giá. Không chuyển nhượng hoặc đổi thành tiền."); wrapMode: Text.WordWrap; color: GlassTheme.muted }
        PaymentText { width: parent.width; visible: root.rewards.enabled; text: Legacy.Tr.phrase("Điểm mỗi ngày")+": "+root.rewards.daily_points+" · "+Legacy.Tr.phrase("Trần giảm giá")+": "+root.rewards.max_percent+"%\n"+(root.rewards.expiry_days ? Legacy.Tr.phrase("Hạn dùng điểm mới (ngày)")+": "+root.rewards.expiry_days : Legacy.Tr.phrase("Điểm mới không hết hạn"))+"\n"+Legacy.Tr.phrase("Nhận một lần mỗi ngày UTC, không cộng bù ngày bỏ lỡ. Điểm đã nhận giữ điều kiện của lô cấp; báo giá xác nhận mức giảm thực tế."); wrapMode: Text.WordWrap; color: GlassTheme.muted }
        PaymentText { width: parent.width; visible: !root.rewards.enabled; text: Legacy.Tr.phrase("Thưởng ngày chưa được mở. Điểm đã nhận giữ điều kiện cũ; coin nạp không bị ảnh hưởng."); wrapMode: Text.WordWrap; color: GlassTheme.muted }
        PaymentText { width: parent.width; visible: root.rewards.next_expiry_at>0; text: (root.rewards.expiring_points||0)+" "+Legacy.Tr.phrase("điểm hết hạn lúc")+" "+root.date(root.rewards.next_expiry_at); wrapMode: Text.WordWrap; color: GlassTheme.muted }
        PaymentText { width: parent.width; visible: root.rewards.claimed_today; text: Legacy.Tr.phrase("Lần nhận tiếp theo")+": "+root.date(root.rewards.next_claim_at); wrapMode: Text.WordWrap; color: GlassTheme.muted }
        Button { objectName: "marketClaimReward"; label: Legacy.Tr.phrase(root.rewards.claimed_today ? "Đã nhận hôm nay" : "Nhận điểm hôm nay"); clickable: root.marketEnabled && socialBridge.signedIn && root.rewards.enabled && root.rewards.member && !root.rewards.claimed_today && !marketBridge.busy; onClicked: marketBridge.claimReward() }
    }
}
