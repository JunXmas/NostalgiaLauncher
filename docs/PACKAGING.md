# Đóng gói bản cài cho Windows và macOS

## Vì sao phải build trên đúng nền tảng đích

Không có cách nào tạo `.exe` hay `.app` từ máy Linux. PyInstaller không dịch mã
nguồn — nó gói lại **đúng** trình thông dịch Python và **đúng** bộ thư viện Qt
đang có trên máy chạy nó. Muốn ra bản Windows thì phải có Python của Windows và
Qt của Windows, tức là phải chạy trên Windows.

Ba đường đi, chọn một:

| Cách | Cần gì | Nhận xét |
|---|---|---|
| **GitHub Actions** | chỉ cần tài khoản GitHub | Nên dùng. Không cần sở hữu máy Mac hay Windows. Đã viết sẵn ở `.github/workflows/build-installers.yml` |
| Máy thật | một máy Windows, một máy Mac | Nhanh khi cần thử đi thử lại |
| Máy ảo | VM Windows chạy được; **macOS thì vướng giấy phép của Apple** | Chỉ khả thi cho Windows |

## Cách dùng GitHub Actions

Đẩy code lên GitHub rồi vào tab **Actions → Build installers → Run workflow**.
Khoảng 10–15 phút sau, ba file nằm ở mục Artifacts:

- `NostalgiaLauncher-0.2.0-Setup.exe` — Windows x64
- `NostalgiaLauncher-0.2.0-arm64.dmg` — Mac chip Apple (M1 trở lên)
- `NostalgiaLauncher-0.2.0-x86_64.dmg` — Mac chip Intel

Gắn tag `v0.2.0` rồi push thì workflow tự tạo luôn một GitHub Release ở dạng
nháp, đã đính sẵn cả ba file.

## Build tay

Bước chung, chạy ở thư mục gốc dự án:

```bash
pip install -r requirements.txt PySide6-Essentials pyinstaller
python packaging/make_icon.py          # sinh icon.ico, icon.icns và bộ PNG
pyinstaller packaging/nostalgia.spec --noconfirm
```

**Windows** — cài thêm [Inno Setup 6.3 trở lên](https://jrsoftware.org/isdl.php)
(bản cũ hơn không hiểu `x64compatible`; ghi chú ngay trong file `.iss` nói cách sửa):

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" packaging\windows\nostalgia.iss
# -> dist\installer\NostalgiaLauncher-0.2.0-Setup.exe
```

**macOS** — mọi công cụ cần đến đều có sẵn trong hệ điều hành:

```bash
bash packaging/macos/build-dmg.sh
# -> dist/installer/NostalgiaLauncher-0.2.0-<kiến trúc>.dmg
```

## Chuyện chữ ký số

Bản cài **chưa được ký**, nên lần mở đầu tiên hệ điều hành sẽ chặn lại. Đây là
hành vi bình thường với phần mềm không ký, không phải lỗi:

- **Windows** — SmartScreen báo "Windows protected your PC".
  Bấm *More info* → *Run anyway*.
- **macOS** — báo "cannot be opened because the developer cannot be verified".
  Bấm chuột phải vào app → *Open* → *Open*. Hoặc vào System Settings →
  Privacy & Security → *Open Anyway*.

Muốn bỏ hẳn cảnh báo thì phải mua chứng thư số, và giá không rẻ: chứng thư ký
mã Windows khoảng 200–400 USD mỗi năm, còn Apple Developer Program là 99 USD
mỗi năm (kèm theo đó là phải nộp app cho Apple notarize). Với một dự án cá nhân
thì hướng dẫn người dùng bấm qua cảnh báo là lựa chọn hợp lý.

Riêng trên Mac chip Apple có một chi tiết bắt buộc: `build-dmg.sh` ký **ad-hoc**
(`codesign -s -`). Không phải để làm đẹp — macOS từ chối nạp mã arm64 hoàn toàn
không có chữ ký, app sẽ bị giết ngay lúc mở. Chữ ký ad-hoc không cần tài khoản
Apple nào cả.

## Dữ liệu người dùng nằm ở đâu

Mỗi hệ điều hành một chỗ, theo đúng quy ước sở tại (xem `nostalgia/paths.py`):

| | Cấu hình & tài khoản | Thư mục game |
|---|---|---|
| Windows | `%APPDATA%\Nostalgia Launcher` | `%APPDATA%\.nostalgia-launcher` |
| macOS | `~/Library/Application Support/Nostalgia Launcher` | `~/Library/Application Support/nostalgia-launcher` |
| Linux | `~/.config/nostalgia-launcher` | `~/.nostalgia-launcher` |

Gỡ cài đặt **không** đụng tới những thư mục này. Gỡ ra cài lại bản mới là việc
thường ngày, mà xoá nhầm thì mất cả tài khoản đã đăng nhập lẫn thế giới đã chơi.

## Còn lại gì chưa chắc chắn

Toàn bộ phần lõi — tải file, chọn Java, dựng dòng lệnh, đường dẫn theo hệ điều
hành — đều đã sửa cho đa nền tảng và kiểm tra được bằng lập luận trên mã nguồn.
Nhưng những thứ chỉ lộ ra khi thật sự chạy thì chưa ai xác nhận, vì chưa có máy
Windows/Mac nào chạy thử:

- **Cửa sổ frameless.** Thanh tiêu đề tự vẽ đang kéo bằng `mouseMoveEvent` thủ
  công. Cách này chạy được ở cả ba nền tảng, nhưng trên Windows sẽ không có
  Aero Snap (kéo cửa sổ vào cạnh màn hình để tự chia đôi). Muốn có thì đổi sang
  `windowHandle().startSystemMove()`.
- **Nền kính.** Hiệu ứng mờ do launcher tự vẽ chứ không nhờ hệ điều hành, nên
  đúng ra là chạy giống nhau ở mọi nơi — chỉ cần nhìn tận mắt một lần cho chắc.
- **Màn hình Retina.** `NSHighResolutionCapable` đã bật trong bundle; cần xem
  lại xem nét vẽ tay có bị lệch nửa điểm ảnh ở tỉ lệ 2x không.
- **Firewall Windows** có thể hỏi một lần khi liên kết tài khoản Google, vì
  bước đó mở một cổng nghe tạm ở `127.0.0.1`.
