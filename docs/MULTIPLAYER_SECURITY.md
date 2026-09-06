# CHƠI CHUNG — mô hình đe doạ và luật thiết kế

Viết TRƯỚC khi code, từ hai nguồn: rà mã multiplayer của launcher cũ (nhánh
`harden/multiplayer-auth`, relay `cloudflare/multiplayer-relay/`) và tra cứu lớp tấn công đã
biết với "LAN qua relay" (e4mc, playit.gg) cùng hạn mức Cloudflare. Mỗi luật ở §3 phải có test
gác; §4 liệt kê tên test.

## 1. Kiến trúc (giữ từ bản cũ)

```
Host:   Minecraft "Open to LAN" ──127.0.0.1:world_port──> launcher-host ──WSS──> relay (Durable Object)
Joiner: Minecraft ──127.0.0.1:local_port──> launcher-joiner ──WSS──> relay
```

- Cả hai máy chỉ nối RA NGOÀI (443) → qua NAT, và **không bên nào thấy IP bên kia**.
- Host mux nhiều joiner trên MỘT WebSocket: khung `[stream_id:4][flag:1][payload]`,
  flag 0 DATA / 1 OPEN / 2 CLOSE. Mỗi joiner một WebSocket riêng, payload thô.
- Mã phòng = `room_id` (6 ký tự, relay thấy, nằm trong URL) + `room_secret` (12 ký tự,
  khoá HMAC, KHÔNG BAO GIỜ lên dây, không lên bất kỳ API nào). Bảng 31 ký tự bỏ 0/O/1/I/L.
- Bắt tay `NLh2` hai chiều: joiner HELLO(nonce) → host CHALLENGE(nonce, HMAC(secret,"host"+nonce_joiner))
  → joiner kiểm rồi RESPONSE(HMAC(secret,"join"+nonce_host)) → host mới mở kết nối tới world.

## 2. Kẻ tấn công và mục tiêu

| Kẻ tấn công | Có gì | Muốn gì |
|---|---|---|
| A. Người lạ trên Internet | biết URL relay công khai | dò phòng đang mở, vào world không mời, chiếm slot host, dùng relay làm proxy chùa, đốt hạn mức Cloudflare |
| B. Bạn cũ / người từng có mã | mã phòng cũ | vào lại khi không còn được mời (replay) |
| C. Host độc | giữ secret hợp lệ | đẩy byte độc vào Minecraft của joiner (packet crash, Log4Shell qua chat, resource pack lừa) |
| D. Joiner độc | giữ secret hợp lệ | đẩy byte độc vào world của host; mở ồ ạt stream làm host cạn RAM |
| E. Tiến trình/máy cùng LAN với host | phát được multicast tới 224.0.2.60:4445 | lừa launcher-host bắc cầu relay tới cổng loopback khác (ssh, DB) — SSRF vào loopback |
| F. Relay bị chiếm / kẻ nghe lén | thấy mọi byte qua relay | lấy secret, replay, giả host |

**Kết luận về "virus/RAT lây qua LAN":** gói vanilla Minecraft không có cơ chế thực thi file
hay mã trên máy bên kia; kênh lây thật là mod/jar/resource pack người dùng tự cài (Fractureiser
2023 đi qua CurseForge, không qua kết nối game). Launcher chống được: (i) không bao giờ tự tải
hay tự cài gì từ host sang joiner qua phòng, (ii) cảnh báo khi server yêu cầu resource pack,
(iii) tiêm `-Dlog4j2.formatMsgNoLookups=true` cho mọi bản (đã có ở `launch/command.py`).

## 3. Luật thiết kế — mỗi luật một lỗ hổng đã thấy

| # | Luật | Chặn | Bằng chứng từ bản cũ |
|---|---|---|---|
| L1 | **Chỉ có bắt tay v2. Không fallback, không downgrade.** Bắt tay hỏng vì bất kỳ lý do gì → đóng, không gửi gì thêm. | A, F | Mọi lỗi khác "host failed auth" đều rơi xuống v1 và gửi **secret plaintext** → host giả chỉ cần im lặng đóng stream là nhận được secret. |
| L2 | **Secret không rời máy dưới bất kỳ dạng nào.** Không vào URL, không vào presence/friends API, không vào log. Chỉ HMAC của nó lên dây. | A, B, F | Bản cũ đẩy cả mã 18 ký tự vào `PUT /presence` không xác thực → ai biết friend-code lấy được phòng. |
| L3 | **Cổng world chỉ tin từ loopback.** Datagram multicast phải có nguồn `127.0.0.1`; cổng trong 1024..65535; launcher chỉ nối tới cổng vừa nghe được. | E | Bản cũ bind `0.0.0.0:4445`, không kiểm nguồn → hàng xóm phát `[AD]22[/AD]` là host bắc cầu tới ssh. |
| L4 | **Byte đầu sau bắt tay phải là gói Handshake Minecraft hợp lệ** (VarInt length ≤ 300, packet id 0x00, next_state ∈ {1,2}). Không đúng → đóng stream. Chỉ chuyển tiếp byte, không diễn giải lệnh. | D | Bản cũ chuyển tiếp bất kỳ byte nào sau bắt tay. |
| L5 | **Trần ở mọi bộ đệm.** Khung WS ≤ 1 MiB (đọc chunk 64 KiB nên không cần hơn), tổng gộp continuation ≤ 1 MiB, bộ đệm bắt tay ≤ 512 B, ≤ 32 stream chưa xác thực, timeout bắt tay 8 s, ≤ 16 joiner. | D, F | Bản cũ 16 MiB/khung — thừa 16 lần. |
| L6 | **Phòng đóng mặc định, hết hạn khi host dừng.** Mã mới mỗi lần host; nút "khoá phòng" (không nhận stream mới). Không có mã ngắn "tương thích ngược" bỏ xác thực. | A, B | Bản cũ: mã ≤ 6 ký tự → secret rỗng → bỏ cửa xác thực. |
| L7 | **Proxy cục bộ bind cứng `127.0.0.1:0`**; host chỉ nối `127.0.0.1:world_port`. Không có tham số đổi địa chỉ. | A | Bản cũ đúng — giữ. |
| L8 | **Relay không phải nơi tin cậy.** Xác thực ở tầng ứng dụng; relay chỉ chặn lạm dụng rẻ: trần khung, rate-limit cả `role=host` lẫn `role=join`, cùng một mã đóng cho "không có host" và "bị rate-limit" để không thành oracle dò `room_id`. | A | Bản cũ trả 4004/4009 trước khi rate-limit → quét 31^6 phòng tự do. |
| L9 | **Client WS kiểm `Sec-WebSocket-Accept`**, SNI + ALPN http/1.1, timeout nối 15 s. | F | Bản cũ chỉ tìm chuỗi "101". |
| L10 | **Mọi luồng nền dừng được và có chủ.** Dừng phòng = huỷ task + đóng socket trong < 2 s; đóng launcher dừng phòng. | — | Bản cũ chỉ dừng khi `aboutToQuit`. |

Ngoài phạm vi (ghi để không quên): friends/presence cần chữ ký từng thiết bị và rate-limit đọc
ở backend — chưa làm; relay sửa theo L8 nằm trong kho nhưng **chỉ deploy khi jun đồng ý**; client
mới vẫn tương thích relay đang chạy vì khung mux không đổi.

## 4. Test gác (tests/multiplayer/)

- L1: `test_handshake_rejects_wrong_secret`, `test_handshake_rejects_replay`, `test_joiner_gives_up_when_host_is_silent`
- L2: `test_secret_never_on_the_wire`
- L3: `test_lan_detect_ignores_non_loopback_source`, `test_lan_detect_rejects_bad_port`
- L4: `test_first_bytes_must_be_minecraft_handshake`
- L5: `test_frame_caps`, `test_pending_streams_capped`
- L6: `test_room_code_has_entropy`, `test_locked_room_refuses_new_streams`
- L7: `test_bridge_binds_loopback_only`
- L9: `test_websocket_accept_is_verified`
- L10: `test_stop_ends_all_tasks`
