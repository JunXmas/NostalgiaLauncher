"""Chơi chung không cần thuê server: "Open to LAN" của host đi qua relay WebSocket tới máy bạn.

Luật thiết kế và mô hình đe doạ ở `docs/MULTIPLAYER_SECURITY.md`. Gói này chỉ dùng stdlib
(`asyncio`, `socket`, `ssl`, `hmac`); không biết gì về bản chơi hay tài khoản.
"""
