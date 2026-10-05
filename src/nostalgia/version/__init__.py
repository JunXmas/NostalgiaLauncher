"""Mô hình phiên bản Minecraft — THUẦN: không chạm mạng, không đọc/ghi file.

Đây là nơi chứa phần lớn độ khó của một launcher: luật `rules` theo hệ điều hành, kế thừa
`inheritsFrom`, hai kiểu khai tham số, và hai kiểu khai natives. Tách thuần ra thì test chạy
offline trong mili-giây, và kiểm được hành vi trên Windows/macOS ngay khi đang ngồi trên
Linux — vì nền tảng là **đối số của hàm**, không phải trạng thái toàn cục.

Bất biến này không được luật tầng bảo vệ (L2 vẫn được import L1), nên có test gác riêng:
`test_version_package_stays_pure`.
"""
