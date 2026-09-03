# Từ điển thuật ngữ — luật đặt tên của kho này

Đây là **luật**, không phải gợi ý. PR đặt tên trái từ điển sẽ bị trả lại.

Lý do có file này: kho tiền nhiệm gọi *thư mục game* bằng bốn tên khác nhau
(`game_dir`, `game_root`, `mc_dir`, `store_root`) và gọi *phiên bản Minecraft* bằng bốn tên
khác nữa (`mc`, `mc_version`, `game_version`, `version_id`). Trong cùng một hàm khởi tạo có
cả `game_dir` lẫn `store_root` mang hai nghĩa khác nhau, phải ba dòng chú thích mới hiểu.
Một khái niệm phải có đúng một tên.

## 1. Quy ước chung

### 1.1 `Path` hay `str`

Mọi thứ chạm hệ thống file là `pathlib.Path`. `str` chỉ được xuất hiện ở đúng ba biên:

- đối số nhận từ dòng lệnh,
- khoá và giá trị trong JSON,
- `argv` truyền cho `subprocess`.

**Không có tham số kiểu `str | Path`.** Chuyển đổi ngay tại biên, không đẩy sâu vào trong.

### 1.2 Tiền tố tên hàm — nhìn tên phải biết hàm có chạm mạng không

| Tiền tố | Nghĩa |
|---|---|
| `resolve_*` | Tính thuần từ dữ liệu đã có. **Không I/O, không mạng.** |
| `load_*` | Đọc từ đĩa. |
| `fetch_*` | **Chạm mạng.** |
| `ensure_*` | Idempotent: có rồi thì thôi, thiếu thì tạo/tải. |
| `build_*` | Dựng cấu trúc trong bộ nhớ. |
| `write_*` / `save_*` | Ghi xuống đĩa. |
| `plan_*` | Trả về danh sách việc cần làm, **không tự làm**. |
| `list_*` / `iter_*` | Liệt kê. |
| `is_*` / `has_*` | Trả `bool`. |
| `verify_*` | Kiểm tra, trả danh sách lỗi (không ném khi chỉ là "chưa đạt"). |

**Cấm:** `get_*`, `do_*`, `handle_*`, `process_*`, `manage_*`. Chúng không nói lên điều gì.

Kho cũ có sáu cách gọi cùng một hành động: `install()`, `ensure()`, `install_file()`,
`install_to_mods()`, `install_contents()`, `apply_to_instance()`. Bảng trên tồn tại để chặn
đúng chuyện đó.

### 1.3 Kiểu dữ liệu

- Mọi dữ liệu đi **giữa các module** là `@dataclass(frozen=True, slots=True)`.
- `dict` thô chỉ được tồn tại **bên trong** lớp phân tích JSON (`version/model.py`).
  Không bao giờ để `dict` đi qua biên module.
- Không trả `tuple` vô danh nhiều phần tử — đặt tên nó thành dataclass.

### 1.4 Trạng thái

- **Không trạng thái toàn cục.** Không singleton, không cache mức module.
- **Không hằng `Path` mức module.** Đường dẫn luôn nằm trong `DataPaths` được truyền vào.
  Đây là luật số một, sinh ra từ lỗi mất dữ liệu của kho cũ (xem mục 4).
- Hằng mức module chỉ được là literal: URL, timeout, tên hệ điều hành.

### 1.5 Tên file và module

- Danh từ số ít. Không `utils.py`, `helpers.py`, `common.py`, `misc.py`, `core.py`.
- Không lặp tên gói: `install/install.py` ❌ → `install/installer.py` ✅.
- **Mỗi file tối đa 200 dòng.** Vượt thì tách.

### 1.6 Ngôn ngữ

- Định danh, tên file, thông điệp lỗi kỹ thuật: **tiếng Anh**.
- Docstring và chú thích: **tiếng Việt**.

Không trộn hai kiểu trong cùng một loại. Kho cũ có một module viết chú thích tiếng Anh và tự
biện minh "để khớp ngôn ngữ nguồn của kho", trong khi toàn bộ phần còn lại là tiếng Việt.

## 2. Bảng thuật ngữ cốt lõi

| Khái niệm | Tên chuẩn | Kiểu | CẤM dùng |
|---|---|---|---|
| Kho chung của launcher (versions, libraries, assets, runtime) | `data_dir` | `Path` | `store_root`, `root`, `base_dir`, `app_dir`, `mc_dir` |
| Bộ đường dẫn dẫn xuất từ `data_dir` | `paths` : `DataPaths` | frozen dataclass | truyền lẻ từng `Path` |
| Thư mục game chạy trong đó (`--gameDir`: saves, options.txt, mods) | `game_dir` | `Path` | `minecraft_dir`, `gamedir`, `run_dir`, `instance_dir` |
| Mã phiên bản (khoá thư mục và tên file JSON) | `version_id` | `str` | `version`, `ver`, `vid`, `id`, `mcver`, `mc` |
| Phiên bản game nền, khi `version_id` là của loader | `game_version` | `str` | `mc_version`, `base_version` |
| Phiên bản cha được kế thừa | `inherits_from` | `str \| None` | `parent`, `base`, `inherit` |
| Metadata phiên bản đã trộn kế thừa xong | `version_meta` : `VersionMeta` | dataclass | `meta`, `data`, `json`, `profile`, `v` |
| Dict JSON thô (chỉ trong lớp parse) | `version_dict` | `dict[str, Any]` | `raw`, `j`, `d` |
| Một bản ghi trong manifest của Mojang | `manifest_entry` : `ManifestEntry` | dataclass | `entry`, `item` |
| Thư viện | `library` / `libraries` : `Library` | dataclass | `lib`, `libs`, `l` |
| Toạ độ maven `group:artifact:version[:classifier]` | `coordinate` : `MavenCoordinate` | dataclass | `coord`, `gav`, `name` |
| Một file tải được (url + đích + sha1 + size) | `artifact` : `Artifact` | frozen dataclass | `download`, `dl`, `art`, tuple ba phần tử |
| Thư viện natives và mã classifier của nó | `native_artifact`, `native_classifier` | `Artifact`, `str` | `natives` khi đang nói về artifact |
| Thư mục natives đã giải nén | `natives_dir` | `Path` | `natives`, `nat_dir` |
| Classpath dạng danh sách | `classpath` | `list[Path]` | `cp`, `cp_list` |
| Classpath đã nối thành chuỗi | `classpath_arg` | `str` | dùng lại tên `classpath` cho cả hai nghĩa |
| Mã asset index (`"5"`, `"1.12"`, `"legacy"`) | `asset_index_id` | `str` | `index`, `assets`, `assets_index_name` |
| Asset index đã phân tích | `asset_index` : `AssetIndex` | dataclass | `idx`, `index_json` |
| Một object asset | `asset_object` : `AssetObject` | dataclass | `obj`, `o`, `asset` |
| Tài khoản lưu trên đĩa | `account` : `Account` | dataclass | `acc`, `user` |
| Khoá định danh tài khoản | `account_id` | `str` | `label`, `key`, `name` |
| Loại tài khoản | `account_kind` : `Literal["offline", "microsoft"]` | | `type`, `kind` trần |
| Danh tính dùng để dựng lệnh chạy (không ghi đĩa) | `player_profile` : `PlayerProfile` | frozen dataclass | `identity`, `LaunchIdentity`, `session` |
| Tên hiển thị trong game | `player_name` | `str` | `username`, `name`, `nick` |
| UUID người chơi (có gạch; `.to_undashed()` khi cần) | `player_uuid` | `str` | `uuid` (đụng tên module), `id` |
| Vé đăng nhập | `access_token` | `str` | `token`, `tk` |
| Bản cài riêng (thư mục game riêng, kho chung) | `instance` : `Instance` | dataclass | `profile`, `pack`, `install` |
| Slug thư mục của bản cài | `instance_id` | `str` | `slug`, `dirname` |
| Loại và phiên bản mod loader | `loader_kind`, `loader_version` | `Literal[...]`, `str` | `modloader`, `loader` trần |
| Component JRE của Mojang (`"jre-legacy"`, `"java-runtime-gamma"`) | `java_component` | `str` | `jre`, `runtime`, `component` trần |
| Số major của Java (8, 17, 21) | `java_major` | `int` | `java_version`, `jv` |
| File thực thi java | `java_binary` | `Path` | `java`, `java_path`, `jvm` |
| Một việc tải | `task` : `DownloadTask` | frozen dataclass | `job`, tuple |
| Báo tiến độ | `on_progress: Callable[[Progress], None]` | | ba đối số rời |
| Yêu cầu dừng | `cancel: CancelToken` | | closure `should_cancel` |
| Tiến trình game đang chạy | `game_process` : `GameProcess` | | `proc`, `p`, `process` trần |

## 3. Bốn cặp dễ lẫn nhất

1. **`data_dir` ≠ `game_dir`.** `data_dir` là kho chung do launcher sở hữu (versions,
   libraries, assets, runtime). `game_dir` là nơi game chạy, do người chơi sở hữu (saves,
   options.txt, mods). Kho cũ gọi cả hai là `game_dir` rồi phải thêm `store_root` để vá.
2. **`version_id` ≠ `version_meta` ≠ file `version.json`.** Một cái là chuỗi, một cái là đối
   tượng đã trộn kế thừa, một cái là file trên đĩa.
3. **`account` ≠ `player_profile`.** `account` lưu lâu dài và chứa bí mật. `player_profile`
   là thứ dẫn xuất, chỉ dùng để dựng lệnh chạy, **không bao giờ ghi xuống đĩa**.
4. **`asset_index_id` ≠ `asset_index` ≠ `assets_dir`.**

## 4. Ba luật có test gác

Vi phạm sẽ làm rớt CI, không cần người soát phát hiện.

| Test | Chặn điều gì |
|---|---|
| `test_no_module_level_path_constants` | Gán ở mức module có chứa `Path.home()`, `os.environ`, `expanduser`. Nguyên nhân gốc của lỗi mất instance ở kho cũ: `CONFIG_DIR, CACHE_DIR, DEFAULT_GAME_DIR = _dirs()` được tính **ngay lúc import**, nên chỉ cần một dòng import sớm là test ghi thẳng vào config thật. |
| `test_layer_imports` | Tầng dưới import tầng trên; module ngoài `net/` import `requests`. |
| `test_core_never_prints` | `print(` xuất hiện ngoài `cli/`. Lõi báo tiến độ qua `on_progress`, báo diễn biến qua `logging`. |

Ba test này được thêm ở bước 2 và chạy trong CI từ đó trở đi.

## 5. Kiến trúc sáu tầng

Phụ thuộc **chỉ đi xuống**. Tầng N import được tầng nhỏ hơn N, không bao giờ ngược lại.

```
L0  errors · platform_info · paths · fsio · progress     không import gì của mccore
L1  net/http · net/download · config
L2  version/  rules · maven · model · inherit · arguments · classpath
        ^ THUẦN: không mạng, không đọc/ghi file
L3  repo/ manifest · version_repo
    install/ client · library · natives · assets · installer
    java/ component · mojang_jre · detect
L4  account/ offline · model · store
    launch/ command · tuning · process · launcher
    doctor
L5  cli/                                       tầng DUY NHẤT được print()
```

Hai luật đáng giá nhất:

- **`version/` không chạm mạng và không đọc/ghi file.** Đây là nơi chứa phần lớn độ khó của
  một launcher (kế thừa, rules, thay thế tham số). Tách thuần ra thì test chạy offline, chạy
  trong mili-giây, và kiểm được hành vi trên Windows/macOS ngay khi đang ngồi trên Linux —
  vì tên hệ điều hành là **đối số của hàm**, không phải trạng thái toàn cục.
- **`install/*` chỉ lập kế hoạch, không tải.** Mỗi module trả `list[DownloadTask]`; việc tải
  gom hết vào `net/download.py`. Nhờ vậy logic cài đặt test được offline: kiểm *danh sách
  task sinh ra* thay vì phải tải thật.
