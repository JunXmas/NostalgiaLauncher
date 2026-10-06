import QtQuick
import "../" as Legacy

Column {
    width: parent.width
    spacing: 12
    visible: typeof serviceConfiguration !== "undefined"
    PaymentText { width: parent.width; font.weight: Font.DemiBold; text: "Dịch vụ Google & Plus · bản draft" }
    PaymentText { width: parent.width; text: "Chỉ nhập URL dịch vụ HTTPS do dự án cung cấp. Không nhập client secret, khóa payOS hoặc token Google."; color: GlassTheme.muted }
    Input { id: account; objectName: "serviceAccountUrl"; width: parent.width; placeholder: "https://dịch-vụ-tài-khoản"; text: typeof serviceConfiguration !== "undefined" ? serviceConfiguration.accountUrl : "" }
    Input { id: relay; width: parent.width; placeholder: "https://dịch-vụ-relay-đồng-bộ"; text: typeof serviceConfiguration !== "undefined" ? serviceConfiguration.roomSyncUrl : "" }
    Button { objectName: "saveServiceSettings"; label: "Lưu cấu hình dịch vụ"; onClicked: serviceConfiguration.save(account.text,relay.text) }
    PaymentText { width: parent.width; text: typeof serviceConfiguration !== "undefined" ? serviceConfiguration.note : ""; color: GlassTheme.accent }
}
