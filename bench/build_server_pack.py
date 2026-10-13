"""Build a versioned server pack and its channel JSON without releasing a launcher."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from nostalgia.content.builtin_receipt import bundle_version
from nostalgia.content.pack_channel import parse_channel
from nostalgia.update.release import is_newer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    arguments = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    source = repository / "src/nostalgia/content/packs/forgotten-worlds-1.21.11.mrpack"
    if not is_newer(arguments.version, bundle_version(source)):
        parser.error("Pack version must be newer than the bundled pack")
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"Forgotten-Worlds-Optimized-{arguments.version}.mrpack"
    destination = arguments.output_dir / filename
    guide = (repository / "modpacks/player-guide.txt").read_bytes()
    with (
        zipfile.ZipFile(source) as archive,
        zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as output,
    ):
        for member in archive.infolist():
            payload = archive.read(member.filename)
            if member.filename == "modrinth.index.json":
                document = json.loads(payload)
                document["versionId"] = arguments.version
                payload = json.dumps(document, ensure_ascii=False, indent=2).encode()
            elif member.filename == "overrides/README-Forgotten-Worlds.txt":
                lines = payload.decode().splitlines()
                lines[0] = "Forgotten Worlds — Optimized " + arguments.version
                payload = ("\n".join(lines) + "\n").encode()
            if member.filename != "overrides/config/forgotten-worlds-guide.txt":
                output.writestr(member, payload)
        output.writestr(zipfile.ZipInfo("overrides/config/forgotten-worlds-guide.txt"), guide)
    payload = destination.read_bytes()
    channel = {
        "format": 1,
        "preset": "forgotten-worlds",
        "version": arguments.version,
        "minecraft": document["dependencies"]["minecraft"],
        "fabric-loader": document["dependencies"]["fabric-loader"],
        "url": "https://github.com/JunXmas/NostalgiaLauncher/releases/download/"
        + f"forgotten-worlds-{arguments.version}/{filename}",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
    }
    parse_channel(channel)
    (arguments.output_dir / "forgotten-worlds.json").write_text(
        json.dumps(channel, indent=2) + "\n", encoding="utf-8"
    )
    print(destination)


if __name__ == "__main__":
    main()
