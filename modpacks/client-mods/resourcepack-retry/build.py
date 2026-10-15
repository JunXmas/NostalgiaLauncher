"""Build the pinned Minecraft 1.21.11 client helper with a supplied classpath."""

import argparse
import hashlib
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classpath", required=True, type=Path)
    parser.add_argument("--javac", default="javac")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    destination = root / "dist/forgottenworlds-rp-retry-1.0.0.jar"
    destination.parent.mkdir(exist_ok=True)
    metadata = {
        "schemaVersion": 1,
        "id": "forgottenworlds_rp_retry",
        "name": "Forgotten Worlds Resource Pack Retry",
        "version": "1.0.0",
        "environment": "client",
        "entrypoints": {"client": ["vn.forgottenworlds.rp.ResourcePackRetryClient"]},
        "mixins": ["forgotten-rp-retry.mixins.json"],
        "depends": {"minecraft": "1.21.11", "fabricloader": ">=0.19.5", "java": ">=21"},
        "license": "LicenseRef-PolyForm-Strict-1.0.0",
    }
    mixins = {
        "required": True,
        "package": "vn.forgottenworlds.rp.mixin",
        "compatibilityLevel": "JAVA_21",
        "client": ["ResourcePackRetryMixin"],
        "injectors": {"defaultRequire": 1},
    }
    with tempfile.TemporaryDirectory() as directory:
        classes = Path(directory)
        result = subprocess.run(
            [
                args.javac,
                "-proc:none",
                "--release",
                "21",
                "-cp",
                args.classpath.read_text().strip(),
                "-d",
                str(classes),
                *map(str, sorted((root / "src").rglob("*.java"))),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise SystemExit(result.stdout + result.stderr)
        with zipfile.ZipFile(destination, "w") as archive:
            entries = {
                p.relative_to(classes).as_posix(): p.read_bytes()
                for p in sorted(classes.rglob("*.class"))
            }
            entries["fabric.mod.json"] = json.dumps(metadata, indent=2).encode()
            entries["forgotten-rp-retry.mixins.json"] = json.dumps(mixins, indent=2).encode()
            for name, payload in sorted(entries.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 10, 15, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, payload)
    print(destination)
    print("sha256=" + hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
