import QtQuick
import "../" as Legacy

PaymentText {
    objectName: "usagePurpose"
    width: parent.width
    text: Legacy.Tr.phrase("Số liệu tổng hợp giúp nhóm phát triển biết phiên bản launcher và hệ điều hành nào còn được dùng, để ưu tiên kiểm thử, sửa lỗi và định hướng các bản tiếp theo.")
    color: GlassTheme.muted
}
