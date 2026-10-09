"""Bản chơi cục bộ có đủ loader và nội dung để kiểm xuất modpack."""

from pathlib import Path

from nostalgia.api import Instance, Launcher
from nostalgia.modloader.model import LoaderKind
from nostalgia.storage.files import atomic_write_json


def prepared_export(tmp_path: Path, loader_kind: LoaderKind = "fabric") -> Launcher:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    game_version = "1.20.1"
    coordinates = {
        "fabric": "net.fabricmc:fabric-loader:0.16.9",
        "quilt": "org.quiltmc:quilt-loader:0.26.0",
        "forge": "net.minecraftforge:forge:1.20.1-47.4.23",
        "neoforge": "net.neoforged:neoforge:21.1.9",
    }
    atomic_write_json(launcher.paths.version_json(game_version), {"id": game_version})
    version_id = (
        game_version
        if loader_kind == "vanilla"
        else {
            "fabric": "fabric-loader-0.16.9-1.20.1",
            "quilt": "quilt-loader-0.26.0-1.20.1",
            "forge": "1.20.1-forge-47.4.23",
            "neoforge": "1.20.1-neoforge-21.1.9",
        }[loader_kind]
    )
    if loader_kind != "vanilla":
        atomic_write_json(
            launcher.paths.version_json(version_id),
            {
                "id": version_id,
                "inheritsFrom": game_version,
                "libraries": [{"name": coordinates[loader_kind]}],
            },
        )
    launcher.save_instance(Instance("custom", version_id, "Gói của tôi"))
    game_dir = launcher.paths.instance_dir("custom")
    for relative_path, body in {
        "mods/local.jar": b"custom mod",
        "mods/optional.jar.disabled": b"disabled mod",
        "resourcepacks/textures.zip": b"textures",
        "shaderpacks/shader.zip": b"shader",
        "config/client.toml": b"settings",
        "kubejs/server_scripts/custom.js": b"script",
        "saves/My world/level.dat": b"world",
        "logs/latest.log": b"private log",
        "mods/.nostalgia-content.json": b"internal",
        "accounts.json": b"private account",
    }.items():
        target = game_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    return launcher
