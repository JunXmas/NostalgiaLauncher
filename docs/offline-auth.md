# Offline Auth Session

Ghi lại cách launcher chạy game khi không có Internet, và vì sao từng chỗ làm như vậy.

## Ba lớp, tách bạch

```
accounts.py   StoredAccount  ->  ai đăng nhập, lưu gì xuống đĩa
              LaunchIdentity ->  bốn tham số game thật sự cần
launch.py     build_command  ->  LaunchIdentity + version JSON -> argv
              launch_game_offline -> đường chạy không chạm mạng
```

Điểm mấu chốt: `build_command()` **không biết** tài khoản thuộc loại nào. Nó chỉ
nhận `LaunchIdentity`, nên thêm một kiểu đăng nhập mới sau này không phải sửa gì
ở tầng dựng lệnh.

```python
@dataclass
class LaunchIdentity:
    username: str      # ${auth_player_name}
    uuid: str          # ${auth_uuid}  (build_command tự bỏ dấu gạch)
    access_token: str  # ${auth_access_token}
    user_type: str     # ${user_type}: "msa" | "offline"
    demo: bool         # bật feature is_demo_user -> game tự thêm --demo
```

## UUID offline: v3, không phải v4

`accounts.offline_uuid()` là bản sao của `UUID.nameUUIDFromBytes()` phía Java:
MD5 của chuỗi `OfflinePlayer:<tên>`, rồi ép version 3 và variant RFC 4122.

Đừng thay bằng `uuid.uuid4()`. Server đặt `online-mode=false` **tự tính lại** UUID
từ tên người chơi bằng đúng công thức trên, và world lưu inventory/toạ độ theo UUID.
Một giá trị ngẫu nhiên sẽ không khớp con số server tính ra, và còn đổi sau mỗi lần
khởi động — mỗi ván chơi thành một người mới, mất sạch đồ. Tính tất định ở đây là
yêu cầu chức năng, không phải chi tiết thẩm mỹ.

Access token dùng chuỗi `"0"`: game chỉ gửi nó đi khi vào server online-mode, mà
đường đó vốn đã đóng với hồ sơ offline.

## Cổng chứng minh quyền sở hữu

`AccountStore.add_offline()` từ chối nếu chưa có tài khoản Microsoft nào sở hữu
game, và `resolve_identity()` **kiểm tra lại lần nữa lúc khởi chạy** — xoá tài khoản
chủ sở hữu đi thì hồ sơ offline tự tụt xuống demo mode thay vì lặng lẽ chạy tiếp.
Cùng cách làm với PrismLauncher (`AccountList::anyAccountIsValid`).

## Phân nhánh khi khởi chạy

```
tài khoản MSA + có mạng   -> refresh token -> install() -> build_command
tài khoản MSA + mất mạng  -> dùng token cache (vẫn chơi đơn được)
hồ sơ offline / --offline -> launch_game_offline()
mất mạng giữa chừng       -> bắt RequestException -> launch_game_offline()
```

Nhánh cuối là lý do `launch_game_offline()` tồn tại. `Installer.install()` *gần như*
chạy được offline sẵn, vì `download()` bỏ qua file đã có và đúng hash. Nhưng chỉ cần
một file lẻ bị thiếu là nó ném `ConnectionError` — **sau khi** đã băm SHA1 vài trăm MB.
Đường offline đảo ngược thứ tự: kiểm tra trước, hỏng trong một phần giây, và nói rõ
thiếu đúng file nào.

Ba khác biệt so với đường thường:

1. `Installer.offline_version_json()` — bản `version_json()` sẽ lặng lẽ gọi manifest
   của Mojang khi thiếu JSON dưới đĩa.
2. `ensure_offline_libraries()` chạy **trước**, không phải sau `install()`.
3. `resolve_java()` chỉ chọn trong những gì đã có; offline không tải JRE hộ được.

## Cây ngoại lệ

| Lỗi | Khi nào | Người dùng thấy gì |
|---|---|---|
| `OwnershipRequired` | thêm hồ sơ offline khi chưa có chủ sở hữu | hướng dẫn chạy `account add` |
| `FileNotFoundError` | thiếu hẳn version JSON | tên file + "chạy online một lần" |
| `OfflineLaunchError` | thiếu jar / libraries / natives | liệt kê tối đa 10 file thiếu |
| *(cảnh báo)* | thiếu assets | vẫn chạy, báo mất âm thanh/bản dịch |

`OfflineLaunchError` kế thừa `RuntimeError` nên chỗ nào đang bắt `RuntimeError` vẫn
chạy như cũ. Thiếu assets **không** chặn khởi động: game vẫn vào được, chỉ mất âm
thanh và bản dịch — chặn ở đây là phạt người dùng vì một thứ không chí mạng.

## Nếu chuyển sang minecraft-launcher-lib

Dự án này tự dựng argv nên không cần thư viện đó. Nếu dùng, ánh xạ như sau — phần
`LaunchIdentity` giữ nguyên, chỉ đổi tầng dựng lệnh:

```python
import minecraft_launcher_lib as mll

def build_options(identity: LaunchIdentity, game_dir: Path) -> dict:
    return {
        "username": identity.username,
        "uuid": identity.uuid,          # vẫn là UUID v3 ở trên, không phải uuid4
        "token": identity.access_token, # "0" cho hồ sơ offline
        "gameDirectory": str(game_dir),
        "demo": identity.demo,
        "launcherName": APP_SLUG,
        "launcherVersion": APP_VERSION,
    }

command = mll.command.get_minecraft_command(version_id, str(game_dir),
                                            build_options(identity, game_dir))
subprocess.Popen(command, cwd=game_dir)
```

`get_minecraft_command()` chỉ đọc version JSON dưới đĩa, không tự đăng nhập — nên nó
đã là "offline" sẵn. Thứ phải tự lo vẫn y hệt: kiểm tra đủ file trước khi chạy
(`mll.install.install_minecraft_version()` mới là hàm chạm mạng), và cổng chứng minh
quyền sở hữu.
