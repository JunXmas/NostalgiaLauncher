"""Mod loader. Mỗi loader chỉ có một nhiệm vụ: ghi ra một file version JSON vào kho.

Sau đó `repo/` trộn kế thừa và `install/` tải đúng như với một bản Mojang — loader không được
có đường cài riêng, vì đường riêng là nơi các lỗi "cài Fabric xong không chạy" của kho tiền
nhiệm sinh ra.
"""
