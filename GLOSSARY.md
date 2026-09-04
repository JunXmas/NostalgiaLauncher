# Từ điển thuật ngữ — luật đặt tên của kho này

Đây là **luật**, không phải gợi ý. PR đặt tên trái từ điển sẽ bị trả lại.

Lý do có file này: kho tiền nhiệm gọi *thư mục game* bằng bốn tên khác nhau
(`game_dir`, `game_root`, `mc_dir`, `store_root`) và gọi *phiên bản Minecraft* bằng bốn tên
khác nữa (`mc`, `mc_version`, `game_version`, `version_id`). Một khái niệm phải có đúng một tên.

## 1. Quy ước chung

### 1.1 Đường dẫn luôn là `Path`

Mọi thứ **chạm hệ thống file** là `pathlib.Path`. Đường dẫn được phép ở dạng `str` chỉ tại ba
biên: đối số nhận từ dòng lệnh, giá trị trong JSON, và `argv` truyền cho `subprocess`.
Chuyển đổi ngay tại biên, không đẩy sâu vào trong. **Không có tham số kiểu `str | Path`.**

Luật này nói về **đường dẫn**. Các khái niệm khác dùng `str` là bình thường — xem cột "Kiểu"
ở bảng §2.

### 1.2 Tiền tố tên hàm — nhìn tên phải biết hàm làm loại việc gì

| Tiền tố | Nghĩa | Chạm mạng? |
|---|---|---|
| `resolve_*` | Tính thuần từ dữ liệu đã có | không, và không cả I/O |
| `load_*` | Đọc từ đĩa | không |
| `write_*` / `save_*` | Ghi xuống đĩa | không |
| `plan_*` | Trả về danh sách việc cần làm, **không tự làm** | không |
| `build_*` | Dựng cấu trúc trong bộ nhớ | không |
| `fetch_*` | Lấy qua mạng | **có** |
| `ensure_*` | Idempotent, **chỉ đụng đĩa**: thiếu thì tạo | không |
| `sync_*` | Idempotent, **được phép tải**: thiếu thì lấy về | **có** |
| `extract_*` | Giải nén archive vào thư mục đích | không |
| `start_*` | Khởi chạy tiến trình con | không |
| `remove_*` | Xoá file hoặc thư mục | không |
| `list_*` / `iter_*` | Liệt kê | tuỳ, phải ghi trong docstring |
| `is_*` / `has_*` | Trả `bool` | không |
| `verify_*` | Kiểm tra, trả danh sách lỗi | không |

**Cấm:** `get_*`, `do_*`, `handle_*`, `process_*`, `manage_*`. Chúng không nói lên điều gì.

`ensure_*` và `sync_*` tách đôi có chủ ý. Kho cũ có sáu cách gọi cùng một hành động
(`install`, `ensure`, `install_file`, `install_to_mods`, `install_contents`,
`apply_to_instance`); bảng trên tồn tại để chặn đúng chuyện đó, và việc tách `ensure`/`sync`
giữ được lời hứa "nhìn tên biết có chạm mạng không" — lời hứa mà một `ensure_*` biết tải sẽ
phá vỡ.

### 1.3 Kiểu dữ liệu

- Mọi dữ liệu đi **giữa các module** là `@dataclass(frozen=True, slots=True)`. **Không có
  ngoại lệ** — cột "Kiểu" ở §2 ghi "dataclass" là viết tắt của đúng dòng này.
- `dict` thô **không bao giờ đi qua biên module**. Module nào parse JSON thì tự chuyển sang
  dataclass ngay trong hàm `load_*`/`fetch_*` của nó. (Nhiều module phải parse JSON:
  `repo/manifest`, `install/assets`, `account/store`, `java/mojang_jre` — luật là về *biên*,
  không phải về *nơi được phép có dict*.)
- Không trả `tuple` vô danh nhiều phần tử — đặt tên nó thành dataclass.

### 1.4 Trạng thái

- **Không trạng thái toàn cục**, không singleton.
- **Không hằng `Path` mức module**, và không cache thứ gì phụ thuộc đường dẫn hoặc I/O.
  Đường dẫn luôn nằm trong `DataPaths` được truyền vào. Đây là luật số một, sinh ra từ lỗi
  mất dữ liệu của kho cũ (§4).
- `@lru_cache` trên **hàm thuần không nhận đường dẫn** thì được phép (ví dụ phân tích toạ độ
  maven, đánh giá `rules`).
- Hằng mức module chỉ được là literal: URL, timeout, tên hệ điều hành.

### 1.5 Tên file và module

- Danh từ số ít. Không `utils.py`, `helpers.py`, `common.py`, `misc.py`, `core.py`.
- Không lặp tên gói: `install/install.py` ❌.
- **Tối đa 200 dòng *code*** (không tính docstring, chú thích, dòng trống). Vượt 250 dòng
  tổng thì phải giải trình trong mô tả PR. Đếm bằng test viết bằng Python — `ruff` không có
  luật giới hạn số dòng mỗi file, và `awk` đếm byte nên sai với tiếng Việt có dấu.

### 1.6 Ngôn ngữ

Định danh, tên file, thông điệp lỗi kỹ thuật: **tiếng Anh**. Docstring và chú thích:
**tiếng Việt**. Không trộn hai kiểu trong cùng một loại.

## 2. Bảng thuật ngữ cốt lõi

Mọi dataclass ở bảng này đều `frozen=True, slots=True` theo §1.3.

| Khái niệm | Tên chuẩn | Kiểu | CẤM dùng |
|---|---|---|---|
| Kho chung của launcher (versions, libraries, assets, runtime) | `data_dir` | `Path` | `store_root`, `root`, `base_dir`, `mc_dir` |
| Bộ đường dẫn dẫn xuất từ `data_dir` | `paths` : `DataPaths` | dataclass | truyền lẻ từng `Path` |
| Thư mục game chạy trong đó (`--gameDir`) | `game_dir` | `Path` | `minecraft_dir`, `run_dir`, `instance_dir` |
| Mã phiên bản | `version_id` | `str` | `version`, `ver`, `vid`, `mcver`, `mc` |
| Phiên bản game nền, khi `version_id` là của loader | `game_version` | `str` | `mc_version`, `base_version` |
| Phiên bản cha được kế thừa | `inherits_from` | `str \| None` | `parent`, `base` |
| Metadata phiên bản đã trộn kế thừa xong | `version_meta` : `VersionMeta` | dataclass | `meta`, `data`, `json`, `profile` |
| Một bản ghi trong manifest của Mojang | `manifest_entry` : `ManifestEntry` | dataclass | `entry`, `item` |
| Thư viện | `library` / `libraries` : `Library` | dataclass | `lib`, `libs` |
| Toạ độ maven `group:artifact:version[:classifier]` | `coordinate` : `MavenCoordinate` | dataclass | `coord`, `gav` |
| **Khai báo một file tải được, do JSON của Mojang mô tả** (url, sha1, size, đường dẫn *tương đối*) | `artifact` : `Artifact` | dataclass | `download`, `dl` |
| **Một việc tải cụ thể**: `Artifact` đã phân giải qua `DataPaths` thành đường dẫn đích *tuyệt đối* | `task` : `DownloadTask` | dataclass | `job`, tuple |
| Thư mục natives đã giải nén | `natives_dir` | `Path` | `natives`, `nat_dir` |
| Classpath dạng danh sách | `classpath` | `list[Path]` | `cp` |
| Classpath đã nối thành chuỗi | `classpath_arg` | `str` | dùng lại tên `classpath` cho cả hai nghĩa |
| Mã asset index (`"5"`, `"legacy"`) | `asset_index_id` | `str` | `index`, `assets` |
| Asset index đã phân tích | `asset_index` : `AssetIndex` | dataclass | `idx`, `index_json` |
| Một object asset | `asset_object` : `AssetObject` | dataclass | `obj`, `asset` |
| Tài khoản lưu trên đĩa | `account` : `Account` | dataclass | `acc`, `user` |
| Khoá định danh tài khoản | `account_id` | `str` | `label`, `key` |
| Loại tài khoản | `account_kind` : `Literal["offline", "microsoft"]` | | `type`, `kind` trần |
| Danh tính dùng để dựng lệnh chạy (không ghi đĩa) | `player_profile` : `PlayerProfile` | dataclass | `identity`, `session` |
| Tên hiển thị trong game | `player_name` | `str` | `username`, `name`, `nick` |
| **UUID người chơi** — giữ cả hai dạng, tránh trộn nhầm hai chuỗi hợp lệ | `player_uuid` : `PlayerUuid` (`.dashed` / `.undashed`) | dataclass | `uuid` (đụng tên module), `id`, và **`str` trần** |
| Vé đăng nhập | `access_token` | `str` | `token`, `tk` |
| Bản cài riêng (thư mục game riêng, kho chung) | `instance` : `Instance` | dataclass | `profile`, `pack` |
| Slug thư mục của bản cài | `instance_id` | `str` | `slug`, `dirname` |
| Loại và phiên bản mod loader | `loader_kind`, `loader_version` | `Literal[...]`, `str` | `modloader`, `loader` trần |
| Component JRE của Mojang | `java_component` | `str` | `jre`, `runtime`, `component` trần |
| Số major của Java | `java_major` | `int` | `java_version` |
| File thực thi java | `java_binary` | `Path` | `java`, `java_path`, `jvm` |
| Báo tiến độ | `on_progress: Callable[[Progress], None]` | | ba đối số rời |
| Yêu cầu dừng | `cancel_token` : `CancelToken` | | `cancel`, `token`, closure `should_cancel` |
| Tiến trình game đang chạy | `game_process` : `GameProcess` | | `proc`, `p`, `process` trần |

## 3. Năm cặp dễ lẫn nhất

1. **`data_dir` ≠ `game_dir`.** `data_dir` là kho chung do launcher sở hữu. `game_dir` là nơi
   game chạy, do người chơi sở hữu. Kho cũ gọi cả hai là `game_dir` rồi vá bằng `store_root`.
2. **`Artifact` ≠ `DownloadTask`.** `Artifact` là thứ Mojang *khai báo* (đường dẫn tương
   đối); `DownloadTask` là thứ ta *sẽ làm* (đường dẫn đích tuyệt đối, đã qua `DataPaths`).
   Hai kiểu có trường gần giống nhau nên rất dễ nhập một — đừng.
3. **`version_id` ≠ `version_meta` ≠ file `version.json`.**
4. **`account` ≠ `player_profile`.** `account` lưu lâu dài và chứa bí mật; `player_profile`
   dẫn xuất, chỉ để dựng lệnh chạy, **không bao giờ ghi xuống đĩa**.
5. **`asset_index_id` ≠ `asset_index` ≠ `assets_dir`.**

## 4. Test gác

Luật viết trong tài liệu mà không ai kiểm thì chỉ là mong muốn. Các test dưới đây soi mã
nguồn bằng `ast`.

**Phạm vi khác nhau theo từng luật:** luật **đặt tên** và **độ dài file** áp cho **cả kho**
(một khái niệm phải mang một tên ở mọi nơi, và luật không chừa cả chính file test). Các luật
còn lại chỉ áp lên `src/mccore/`, vì `bench/` buộc phải in ra màn hình và phải có đường dẫn
mặc định.

| Test | Chặn điều gì | Phạm vi |
|---|---|---|
| `test_every_module_has_a_declared_layer` | Module không có tầng trong sơ đồ | `src/` |
| `test_layer_imports_only_go_down_or_sideways` | Tầng dưới import tầng trên | `src/` |
| `test_imports_have_no_cycles` | Chu trình import, kể cả module tự import chính nó | `src/` |
| `test_version_package_stays_pure` | `version/` import `net/`, hoặc gọi `open`/`read_text`/`write_text`/`mkdir` | `src/version/` |
| `test_no_module_level_path_constants` | Gán mức module chứa `Path.home()`, `expanduser`, `os.environ`, `getenv` | `src/` |
| `test_core_never_prints` | `print(` ngoài `cli/` | `src/` |
| `test_naming_follows_the_glossary` | Tiền tố hàm bị cấm, hoặc tên trong cột "CẤM dùng" của §2 | **cả kho** |
| `test_files_stay_short` | File vượt 200 dòng **code** | **cả kho** |
| `test_only_the_net_package_touches_http_and_tls` | Module ngoài `net/` import `http.client` hoặc `ssl` | `src/` |
| `test_fast_path_does_not_load_heavy_modules` | `mccore --version` kéo theo `http.client`, `ssl`, `zipfile`, `concurrent.futures`, `subprocess` hoặc `logging` | `src/` |

**Danh sách tên cấm đọc THẲNG từ bảng §2 ở trên, không chép tay.** Chép tay thì tài liệu và
test trôi khỏi nhau — và đã trôi thật: có lúc GLOSSARY cấm 70 tên trong khi test chỉ gác 32,
tức hơn một nửa luật không được kiểm. Nay thêm một tên vào cột "CẤM dùng" là nó có hiệu lực
ngay, không phải sửa test. Chỉ định danh nằm trong dấu backtick mới được tính, nên văn xuôi
trong ô đó không biến thành tên cấm; tên do `import` đưa vào cũng được bỏ qua (nếu không,
`import json` bị báo vi phạm vì `json` là bí danh bị cấm của `version_meta`).

Có một danh sách miễn trừ ngắn cho những tên Python ép ta phải dùng (`name`, `id`, `type`,
`key`, `index`, `str`, `process`) — mỗi mục kèm lý do, và danh sách đó phải luôn ngắn.

Cả mười đã được kiểm bằng cách **cố tình vi phạm từng luật một** — 15 ca vi phạm, bắt đủ 15,
gồm cả chuỗi import sâu 300 tầng (không tràn stack) và module tự import chính nó. Một test
gác chưa từng thấy rớt là một test gác chưa biết có hoạt động không.

Lưu ý vì sao cần *cả hai* lớp bảo vệ đường dẫn: lệnh import chạy lúc pytest **thu thập**
test, tức trước khi fixture kịp vá `Path.home`. Nên lưới lúc chạy trong `conftest.py` về
nguyên tắc **không thể** bắt được hằng `Path.home()` ở mức module — đã kiểm bằng đột biến và
đúng là lọt. Chỉ test đọc mã nguồn bắt được nó.

## 5. Kiến trúc bảy tầng

Phụ thuộc **chỉ đi xuống hoặc ngang**. Tầng N import được tầng < N và **được import cùng
tầng**, nhưng đồ thị import phải **phi chu trình** — `test_layer_imports` kiểm cả hai.

```
src/mccore/
  errors.py                      L0  từ vựng lỗi — ở gốc vì mọi tầng đều dùng
  storage/                       L0  đĩa
    paths.py                         DataPaths: cái gì nằm ở đâu
    files.py                         đọc/ghi an toàn, ghi nguyên tử, chống zip-slip
  system/                        L0  máy đang chạy
    platform_info.py                 nhận diện OS và kiến trúc theo từ vựng Mojang
  operations/                    L0  điều khiển thao tác dài
    progress.py                      báo tiến độ
    cancellation.py                  yêu cầu dừng
  model/                         L0  dataclass dùng chung: ZERO import của mccore
    download.py                      Artifact (tương đối) và DownloadTask (tuyệt đối)
    json_value.py                    kiểu cho JSON chưa tin được, kèm hàm thu hẹp kiểu
  net/                           L1  http, download
  version/                       L2  THUẦN: không mạng, không đọc/ghi file
    rules.py                         luật theo OS/arch/feature; luật sau ghi đè luật trước
    maven.py                         toạ độ và đường dẫn trong libraries/
    meta.py                          phân tích JSON phiên bản của mọi đời
    inherit.py                       trộn inheritsFrom, chặn vòng tròn
    classpath.py                     lọc rules, bỏ natives, gộp trùng giữ bản đầu
    arguments.py                     (bước 11)
  java/component.py              L2  ánh xạ thuần version_meta -> java_component
  repo/                          L3  kho phiên bản
    endpoints.py                     mọi địa chỉ máy chủ, gom một chỗ
    manifest.py                      danh mục 909 bản; bảng tra, không quét tuyến tính
    version_repo.py                  load_* đĩa, fetch_* mạng, sync_* phối hợp
  install/                       L3  CHỈ lập kế hoạch, không tự tải
    client.py, library.py            (bước 6)
    natives.py                       giải nén, LÀM PHẲNG vì JVM không tìm đệ quy
    assets.py                        gộp trùng hash; cây tên cho đời <=1.6
    plan.py                          (bước 13)
  java/                          L3  mojang_jre, detect
  account/                       L4  offline, profile, store
  launch/                        L4  command, tuning, game_process, runner
  doctor.py                      L4  soi mắt xích hỏng
  api.py                         L5  façade duy nhất cho giao diện
  cli/                           L6  tầng DUY NHẤT được print()
  config.py                      L6  chỉ cli/ được đọc
```

Tên folder nói **chức năng**, tên file nói **thứ cụ thể**. Không viết tắt: `fsio` đã đổi
thành `storage/files.py`, `cancel` thành `operations/cancellation.py` — người kế thừa dự án
đọc tên là hiểu, không phải đoán.

`tests/` soi gương cây trên: `tests/storage/test_paths.py`, `tests/operations/
test_cancellation.py`. Riêng các test soi cả kho (`test_architecture.py`,
`test_conventions.py`) nằm ở gốc `tests/` cùng `source_tree.py` mà chúng dùng chung.

Bảy quyết định đằng sau sơ đồ này:

1. **`version/` (L2) không chạm mạng và không đọc/ghi file.** Đây là nơi chứa phần lớn độ
   khó của một launcher (kế thừa, rules, thay thế tham số). Tách thuần ra thì test chạy
   offline, chạy trong mili-giây, và kiểm được hành vi trên Windows/macOS ngay khi đang ngồi
   trên Linux — vì tên hệ điều hành là **đối số của hàm**, không phải trạng thái toàn cục.
   Luật tầng *không* đủ để bảo vệ điều này (L2 vẫn được import L1), nên có test riêng.
2. **`model` nằm ở L0.** `net/download` (L1) phải nhận `DownloadTask`, còn `install/` (L3)
   là nơi sinh ra chúng. Nếu kiểu đó định nghĩa trong `install/` thì L1 phải import L3 — vi
   phạm luật vàng ngay ở bước 3. Đặt mọi dataclass dùng chung ở L0 để không ai phải nhìn lên.
3. **`install/` chỉ lập kế hoạch, không tải.** Mỗi module trả `list[DownloadTask]`; module
   gom kế hoạch tên là `plan.py`, không phải `installer.py`. Việc *thực thi* kế hoạch (gọi
   `net/download`, giải nén, ghi kết quả) thuộc `api` ở L5. Nhờ đó toàn bộ logic cài đặt test
   được offline: kiểm *danh sách task sinh ra* thay vì phải tải thật.
4. **`api` là một tầng riêng, không phải một file trong `cli/`.** Giao diện tương lai chỉ
   được import `mccore.api`, `mccore.errors`, `mccore.operations` và các dataclass ở `model`.
   Nếu để `cli/` gọi thẳng L4 thì khi dựng GUI sẽ phát hiện toàn bộ logic điều phối nằm
   trong `cli/` và phải viết lại.
5. **`config` chỉ `cli/` được đọc**, rồi truyền xuống dưới dạng dataclass — giống hệt cách
   `DataPaths` được xử lý. Nếu để tầng dưới đọc `config`, nó thành cửa hậu cho trạng thái
   toàn cục, đúng thứ §1.4 cấm.
6. **`java/component` ở L2, `java/mojang_jre` ở L3.** Chọn component là ánh xạ thuần từ
   `version_meta`; chỉ việc tải JRE mới cần mạng. Gộp chung thì mất quyền test ở tầng thuần.
7. **`launch/game_process`** chứ không phải `launch/process`, để không đụng với tiền tố hàm
   bị cấm `process_*` và tên biến bị cấm `process`.
