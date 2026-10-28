"""Java nâng cao: bản chơi chọn file java riêng; để trống thì vẫn tự chọn bản Mojang như cũ."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Instance
from nostalgia.errors import InstanceError
from test_api import make_launcher


def test_instance_java_override_is_used_saved_and_checked(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher.install_version(VERSION_ID)
    launcher.create_instance(Instance(instance_id="thu", version_id=VERSION_ID))
    launcher.add_offline_account("Jun")

    lines: list[str] = []
    assert launcher.launch_instance("thu", "Jun", on_output=lines.append).wait(timeout=30) == 0
    assert any("fake java" in line for line in lines), "để trống: vẫn là Java Mojang tự chọn"

    custom = tmp_path / "jdk" / "bin" / "java"
    custom.parent.mkdir(parents=True)
    custom.write_text("#!/bin/sh\necho java rieng\n")
    custom.chmod(0o755)
    instance = next(i for i in launcher.list_instances() if i.instance_id == "thu")
    launcher.save_instance(replace(instance, java_binary_override=str(custom)))
    assert launcher.list_instances()[0].java_binary_override == str(custom), "phải lưu qua đĩa"

    lines.clear()
    assert launcher.launch_instance("thu", "Jun", on_output=lines.append).wait(timeout=30) == 0
    assert any("java rieng" in line for line in lines), lines

    custom.unlink()
    with pytest.raises(InstanceError, match="Java đã chọn"):
        launcher.launch_instance("thu", "Jun")
