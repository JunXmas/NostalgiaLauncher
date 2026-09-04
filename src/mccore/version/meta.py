"""Phân tích JSON phiên bản của Mojang thành dataclass đã kiểm định.

Hàm ở đây nhận một `dict` đã parse và trả về dataclass — **không đọc file**. Nhờ vậy toàn bộ
độ khó của định dạng (hai kiểu tham số, hai kiểu natives, `rules`) được test offline bằng
fixture cắt từ file thật.

Ba khác biệt giữa các đời mà mã phải chịu được cùng lúc:

- **Tham số**: đời ≤1.12 dùng `minecraftArguments` là MỘT CHUỖI; đời ≥1.13 dùng
  `arguments.game` và `arguments.jvm` là DANH SÁCH, trong đó phần tử có thể là chuỗi hoặc là
  đối tượng `{rules, value}`.
- **Natives**: đời ≤1.18 khai `natives: {linux: "natives-linux"}` cộng
  `downloads.classifiers`; đời ≥1.19 khai natives thành thư viện riêng có `rules.os`.
- **Kế thừa**: bản của Fabric/Forge chỉ có vài khoá và trỏ về bản gốc qua `inheritsFrom`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from mccore.model.download import Artifact, RemoteFile
from mccore.model.json_value import JsonValue, as_integer, as_list, as_mapping, as_string
from mccore.version.maven import MavenCoordinate
from mccore.version.rules import Rule, parse_rules


@dataclass(frozen=True, slots=True)
class ArgumentSpec:
    """Một hoặc nhiều tham số, kèm điều kiện áp dụng.

    Đời cũ không có `rules`, nên `rules` rỗng nghĩa là luôn áp — đúng ngữ nghĩa của
    `rules_allow`.
    """

    values: tuple[str, ...]
    rules: tuple[Rule, ...] = ()


@dataclass(frozen=True, slots=True)
class Library:
    """Một thư viện, đủ thông tin cho cả hai kiểu khai natives."""

    coordinate: MavenCoordinate
    rules: tuple[Rule, ...] = ()
    artifact: Artifact | None = None
    classifier_artifacts: Mapping[str, Artifact] = field(default_factory=dict)
    natives_classifier_by_os: Mapping[str, str] = field(default_factory=dict)
    extract_excludes: tuple[str, ...] = ()

    @property
    def is_native_bundle(self) -> bool:
        """Thư viện chỉ chứa natives (kiểu cũ): không vào classpath, chỉ để giải nén."""
        return bool(self.natives_classifier_by_os)


@dataclass(frozen=True, slots=True)
class AssetIndexRef:
    """Trỏ tới chỉ mục asset.

    Giữ `RemoteFile` chứ không phải `Artifact`: Mojang không khai đường dẫn cho chỉ mục, nơi
    lưu nó do `DataPaths.asset_index_json` quyết định. `total_size` là tổng dung lượng mọi
    object, dùng để báo tiến độ trước khi tải.
    """

    asset_index_id: str
    remote: RemoteFile
    total_size: int | None = None


@dataclass(frozen=True, slots=True)
class JavaRuntimeRef:
    """Bản Java mà Mojang chỉ định. `component` mới là thứ để tra, không phải `major_version`."""

    java_component: str
    major_version: int | None = None


@dataclass(frozen=True, slots=True)
class VersionMeta:
    """Một phiên bản đã phân tích và đã trộn kế thừa xong."""

    version_id: str
    main_class: str
    inherits_from: str | None = None
    jar_version_id: str | None = None
    release_type: str | None = None
    assets_id: str | None = None
    asset_index: AssetIndexRef | None = None
    java_runtime: JavaRuntimeRef | None = None
    client: RemoteFile | None = None
    libraries: tuple[Library, ...] = ()
    minecraft_arguments: str | None = None
    game_arguments: tuple[ArgumentSpec, ...] = ()
    jvm_arguments: tuple[ArgumentSpec, ...] = ()

    @property
    def uses_legacy_arguments(self) -> bool:
        """Đời ≤1.12: tham số nằm trong một chuỗi duy nhất, không có `rules`."""
        return self.minecraft_arguments is not None and not self.game_arguments

    @property
    def jar_owner_id(self) -> str:
        """Phiên bản nào sở hữu file jar cần dùng.

        Bản của Fabric không có jar riêng: khoá `jar` (hoặc bản gốc sau khi trộn kế thừa)
        chỉ ra rằng phải dùng jar của bản vanilla. Trỏ sai chỗ này là lỗi "không tìm thấy
        client.jar" rất khó truy.
        """
        return self.jar_version_id or self.version_id


def parse_version_meta(version_dict: dict[str, JsonValue]) -> VersionMeta:
    """Phân tích JSON phiên bản. Khoá lạ bị bỏ qua để Mojang thêm khoá mới không làm nổ."""
    arguments = as_mapping(version_dict.get("arguments"))
    downloads = as_mapping(version_dict.get("downloads"))
    return VersionMeta(
        version_id=as_string(version_dict.get("id")) or "",
        main_class=as_string(version_dict.get("mainClass")) or "",
        inherits_from=as_string(version_dict.get("inheritsFrom")),
        jar_version_id=as_string(version_dict.get("jar")),
        release_type=as_string(version_dict.get("type")),
        assets_id=as_string(version_dict.get("assets")),
        asset_index=_parse_asset_index(as_mapping(version_dict.get("assetIndex"))),
        java_runtime=_parse_java_runtime(as_mapping(version_dict.get("javaVersion"))),
        client=_parse_remote_file(as_mapping(downloads.get("client"))),
        libraries=_parse_libraries(as_list(version_dict.get("libraries"))),
        minecraft_arguments=as_string(version_dict.get("minecraftArguments")),
        game_arguments=_parse_arguments(arguments.get("game")),
        jvm_arguments=_parse_arguments(arguments.get("jvm")),
    )


def _parse_arguments(raw_arguments: JsonValue) -> tuple[ArgumentSpec, ...]:
    """Mỗi phần tử là chuỗi trần, hoặc `{rules, value}` với `value` là chuỗi hay danh sách."""
    specs = []
    for argument in as_list(raw_arguments):
        if isinstance(argument, str):
            specs.append(ArgumentSpec(values=(argument,)))
            continue
        if not isinstance(argument, dict):
            continue
        raw_value = argument.get("value")
        values = (
            (raw_value,)
            if isinstance(raw_value, str)
            else tuple(value for value in as_list(raw_value) if isinstance(value, str))
        )
        if values:
            specs.append(ArgumentSpec(values=values, rules=parse_rules(argument.get("rules"))))
    return tuple(specs)


def _parse_libraries(raw_libraries: list[JsonValue]) -> tuple[Library, ...]:
    """Bỏ qua mục không khai `name`.

    Trước đây chỗ này truyền `":::"` vào bộ phân tích toạ độ để khỏi nổ, và kết quả là một
    thư viện có group/artifact/version rỗng lọt vào danh sách. Bỏ qua thì thà thiếu một mục
    còn hơn mang theo một mục vô nghĩa mà tầng trên phải tự phát hiện.
    """
    libraries = []
    for raw_library in raw_libraries:
        library_fields = as_mapping(raw_library)
        coordinate_text = as_string(library_fields.get("name"))
        if coordinate_text is None:
            continue
        libraries.append(_parse_library(library_fields, MavenCoordinate.parse(coordinate_text)))
    return tuple(libraries)


def _parse_library(library_fields: dict[str, JsonValue], coordinate: MavenCoordinate) -> Library:
    downloads = as_mapping(library_fields.get("downloads"))
    classifiers = {
        name: artifact
        for name, raw in as_mapping(downloads.get("classifiers")).items()
        if (artifact := _parse_artifact(as_mapping(raw))) is not None
    }
    extract = as_mapping(library_fields.get("extract"))
    return Library(
        coordinate=coordinate,
        rules=parse_rules(library_fields.get("rules")),
        artifact=_parse_artifact(as_mapping(downloads.get("artifact"))),
        classifier_artifacts=classifiers,
        natives_classifier_by_os={
            name: value
            for name, raw in as_mapping(library_fields.get("natives")).items()
            if (value := as_string(raw)) is not None
        },
        extract_excludes=tuple(
            pattern for pattern in as_list(extract.get("exclude")) if isinstance(pattern, str)
        ),
    )


def _parse_remote_file(raw: dict[str, JsonValue]) -> RemoteFile | None:
    """Phân tích khối `{url, sha1, size}`. Không có `url` thì không có gì để tải."""
    url = as_string(raw.get("url"))
    if url is None:
        return None
    return RemoteFile(url=url, sha1=as_string(raw.get("sha1")), size=as_integer(raw.get("size")))


def _parse_artifact(raw: dict[str, JsonValue]) -> Artifact | None:
    """Như trên, nhưng máy chủ có khai `path` — bắt buộc, vì đó là điều phân biệt hai kiểu."""
    remote = _parse_remote_file(raw)
    path = as_string(raw.get("path"))
    if remote is None or path is None:
        return None
    return Artifact(remote=remote, relative_path=path)


def _parse_asset_index(raw: dict[str, JsonValue]) -> AssetIndexRef | None:
    asset_index_id = as_string(raw.get("id"))
    url = as_string(raw.get("url"))
    if asset_index_id is None or url is None:
        return None
    return AssetIndexRef(
        asset_index_id=asset_index_id,
        remote=RemoteFile(
            url=url, sha1=as_string(raw.get("sha1")), size=as_integer(raw.get("size"))
        ),
        total_size=as_integer(raw.get("totalSize")),
    )


def _parse_java_runtime(raw: dict[str, JsonValue]) -> JavaRuntimeRef | None:
    java_component = as_string(raw.get("component"))
    if java_component is None:
        return None
    return JavaRuntimeRef(
        java_component=java_component, major_version=as_integer(raw.get("majorVersion"))
    )
