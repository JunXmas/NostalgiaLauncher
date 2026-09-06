"""Máy chủ Fabric meta giả dùng chung: danh sách loader và profile JSON cho bản giả 1.99.9."""

from __future__ import annotations

import json

from fake_mojang import VERSION_ID
from local_https_server import ServerState

LOADER_VERSION = "0.16.9"
FABRIC_VERSION_ID = f"fabric-loader-{LOADER_VERSION}-{VERSION_ID}"


def publish_fabric(state: ServerState) -> None:
    state.add(
        f"/fabric/versions/loader/{VERSION_ID}",
        json.dumps(
            [
                {"loader": {"version": "0.17.0-beta.1", "stable": False}},
                {"loader": {"version": LOADER_VERSION, "stable": True}},
            ]
        ).encode(),
    )
    state.add(
        f"/fabric/versions/loader/{VERSION_ID}/{LOADER_VERSION}/profile/json",
        json.dumps(
            {
                "id": FABRIC_VERSION_ID,
                "inheritsFrom": VERSION_ID,
                "type": "release",
                "mainClass": "net.fabricmc.loader.impl.launch.knot.KnotClient",
                "arguments": {
                    "game": [],
                    "jvm": ["-DFabricMcEmu= net.minecraft.client.main.Main"],
                },
                "libraries": [],
            }
        ).encode(),
    )
