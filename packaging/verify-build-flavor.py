"""Reject a packaged binary whose archive does not match the selected build flavor."""

import os
from pathlib import Path

from PyInstaller.archive.readers import ZlibArchiveReader


def main() -> None:
    flavor = os.environ.get("NOSTALGIA_BUILD_FLAVOR", "release")
    if flavor not in ("release", "review"):
        raise ValueError("Unknown build flavor")
    archive = ZlibArchiveReader(str(Path("build/nostalgia-ui/PYZ-00.pyz")))
    review_modules = [name for name in archive.toc if name.startswith("nostalgia_draft")]
    if ("nostalgia_draft.runtime" in review_modules) != (flavor == "review"):
        raise ValueError("Packaged entry does not match the selected flavor")
    if flavor == "release" and review_modules:
        raise ValueError("Production archive contains owner review adapters")


if __name__ == "__main__":
    main()
