"""Real vendor edge cases: Folia Alpha and a verified upstream hybrid bootstrap failure."""

from pathlib import Path

from nostalgia.model.json_value import as_list, as_mapping
from nostalgia.server.catalog import ARCLIGHT_URL, BROKEN_SHA256, PAPER_URL, ServerCatalog
from server_fixture import server_launcher


def test_folia_alpha_is_selectable_but_paper_alpha_is_not(tmp_path: Path) -> None:
    _launcher, http_client = server_launcher(tmp_path)
    server_catalog = ServerCatalog(http_client)
    for engine in ("paper", "folia"):
        url = PAPER_URL + engine + "/versions/1.21.1/builds"
        rows = as_list(http_client.document(url))
        http_client.overrides[url] = [as_mapping(rows[0]) | {"channel": "ALPHA"}]
        assert bool(server_catalog.builds(engine, "1.21.1")) == (engine == "folia")


def test_known_bad_forge_digest_cannot_be_installed_as_latest(tmp_path: Path) -> None:
    _launcher, http_client = server_launcher(tmp_path)
    server_catalog = ServerCatalog(http_client)
    releases = as_list(http_client.document(ARCLIGHT_URL))
    release = as_mapping(releases[0])
    release_files = [as_mapping(remote_file) for remote_file in as_list(release["assets"])]
    release_files[0] = release_files[0] | {"digest": "sha256:" + next(iter(BROKEN_SHA256))}
    http_client.overrides[ARCLIGHT_URL] = [release | {"assets": release_files}]
    assert server_catalog.versions("arclight-forge") == ()
    assert server_catalog.builds("arclight-forge", "1.21.1") == ()
    assert server_catalog.builds("arclight-neoforge", "1.21.1")
