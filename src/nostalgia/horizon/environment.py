"""Môi trường riêng: không kế thừa telemetry hoặc presence của launcher Horizon."""

from pathlib import Path

from nostalgia.system.child_env import clean_child_env


def build_horizon_environment(game_dir: Path) -> dict[str, str]:
    environment = clean_child_env()
    for field in (
        "HORIZON_SESSION_FILE",
        "HORIZON_PLAYER_NAME",
        "HORIZON_OFFLINE_SKIN",
        "HORIZON_OFFLINE_SKIN_MODEL",
        "HORIZON_OFFLINE_CAPE",
    ):
        environment.pop(field, None)
    environment.update(
        HORIZON_HOME=str(game_dir),
        HORIZON_TELEMETRY_URL="off",
        HORIZON_NO_HEARTBEAT="1",
        HORIZON_NO_DISCORD="1",
        HORIZON_COSMETICS="0",
    )
    return environment
