# Phần máy chủ — mã nguồn nằm ở kho riêng

Relay chơi chung và proxy CurseForge chạy trên Cloudflare Worker của chính dự án, và mã
của chúng **không nằm trong kho này**.

| Dịch vụ | Địa chỉ | Làm gì |
|---|---|---|
| Relay chơi chung | `wss://nostalgia-multiplayer-relay.junbob.workers.dev` | Chuyển tiếp byte giữa host và joiner. Hai máy chỉ nối ra ngoài cổng 443 nên qua được NAT, và **không bên nào thấy IP bên kia**. |
| Proxy CurseForge | `https://nostalgia-backend.junbob.workers.dev/cf` | Giữ khoá API CurseForge để người dùng không phải tự đi xin. |

## Vì sao tách ra

Mã chạy trên máy người dùng thì gỡ gói ra là đọc được — obfuscate chỉ là gờ giảm tốc.
Mã chạy trên máy chủ thì không. Nên ranh giới đóng/mở của dự án đặt đúng ở đó, chứ không
chia theo "tính năng thường / tính năng hay":

- **Toàn bộ launcher công khai, AGPL-3.0.** Đây là phần mềm giữ token đăng nhập Microsoft
  của bạn. Phần mềm loại đó mà đóng mã thì không có lý do gì để tin. Mọi dòng chạy trên
  máy bạn đều đọc được, sửa được, tự build lại được.
- **Hai Worker giữ riêng**, vì chúng giữ khoá API và vì đó là thứ duy nhất giữ kín được thật.

## Relay làm gì — kiểm chứng được mà không cần mã của nó

[`docs/MULTIPLAYER_SECURITY.md`](../docs/MULTIPLAYER_SECURITY.md) mô tả đầy đủ mô hình đe
doạ và 10 luật thiết kế. Điều quan trọng nhất kiểm được **ngay trong kho này**, vì nó nằm
ở phía client:

- **Relay không được tin.** Xác thực chạy ở tầng ứng dụng bằng HMAC giữa host và joiner
  (`src/nostalgia/multiplayer/handshake.py`). Relay chỉ thấy byte đã bắt tay xong.
- **Mã phòng không bao giờ lên dây.** Chỉ HMAC của nó đi qua relay — gác bởi
  `tests/multiplayer/test_handshake.py::test_secret_never_on_the_wire`.
- Nghĩa là: kể cả relay bị chiếm, kẻ chiếm nó cũng không giả được host và không lấy được
  mã phòng của bạn. Tuyên bố đó không phụ thuộc vào việc bạn tin mã relay hay không —
  nó được bảo đảm bởi code bạn đang đọc.

Không thích chạy qua relay của dự án? `src/nostalgia/repo/endpoints.py` để địa chỉ ở một
chỗ duy nhất — đổi sang Worker của bạn được, giao thức mô tả đủ trong file bảo mật ở trên.

## `/donate` — số tài khoản nhận ủng hộ

Endpoint thứ ba trên cùng Worker `nostalgia-backend`, và là endpoint đơn giản nhất: trả về
số tài khoản hiện hành để đổi số **không phải ra bản launcher mới**.

```
GET https://nostalgia-backend.junbob.workers.dev/donate
→ 200 {"bin": "970436", "number": "1234567890", "holder": "NGUYEN VAN A"}
```

Ba trường đều bắt buộc và đều là chuỗi; `bin` và `number` phải toàn chữ số. Thiếu một
trường là launcher bỏ cả câu trả lời và dùng số ghim sẵn — một tài khoản nửa vời dựng ra mã
QR mà app ngân hàng từ chối, tệ hơn hẳn số cũ vẫn quét được.

**Không có endpoint này thì tính năng vẫn chạy.** Số tài khoản ghim trong
`src/nostalgia/repo/endpoints.py`; Worker 404, 500, hay máy người dùng offline đều chỉ làm
launcher giữ nguyên số ghim và ghi một dòng log `warning`. Gác bởi
`tests/donate/test_donate_facade.py`.

Không phải bí mật, nên không cần khoá: mã QR chuyển khoản dán ở quán cà phê cũng chính là
ba trường này, và biết số tài khoản chỉ gửi tiền VÀO được chứ không rút ra.
