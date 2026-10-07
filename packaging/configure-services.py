"""Embed public service origins supplied by the project owner; never embed OAuth secrets."""

from __future__ import annotations

import os
from pathlib import Path

from nostalgia.social.configuration import ServiceConfiguration, verify_service_url
from nostalgia.storage.files import atomic_write_json


def main() -> None:
    configuration = ServiceConfiguration(
        verify_service_url(os.environ.get("NOSTALGIA_BUILD_ACCOUNT_URL", "")),
        verify_service_url(os.environ.get("NOSTALGIA_BUILD_ROOM_SYNC_URL", "")),
    )
    path = Path(__file__).resolve().parent.parent / "src/nostalgia/social/service-defaults.json"
    atomic_write_json(
        path,
        {
            "account_url": configuration.account_url,
            "room_sync_url": configuration.room_sync_url,
        },
    )
    print(
        "Google service bundled"
        if configuration.account_url
        else "Google unavailable: owner setup pending"
    )


if __name__ == "__main__":
    main()
