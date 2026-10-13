# Independent Forgotten Worlds updates

The launcher checks `modpacks/forgotten-worlds.json` on GitHub separately from
launcher releases. The status check runs in the background at startup; the server
pack manager also has a manual check button. Reading instance rows uses the cached
channel and never makes a network request. An offline check preserves the cache
and the installed instance.

The first supporting launcher is rc37. rc36 can update only from its bundled
pack, so users must upgrade once. Later pack releases require no launcher upgrade
as long as they use the supported Minecraft/Fabric target.

## Publish a pack

The **Server modpack** GitHub Actions workflow accepts a pack version and performs
these steps on `main`, using GitHub's release credentials. It publishes the pack
asset first, then advances the channel. From the CLI:

```sh
gh workflow run server-pack.yml --ref main -f version=1.0.3
```

If branch protection prevents the final channel commit, the uploaded release is
kept and the generated channel JSON can be submitted through a normal PR.

The equivalent manual procedure is:

1. Update the bundled pack's mod files and/or `modpacks/player-guide.txt`.
2. Build a pack with a new monotonically increasing version:

   ```sh
   uv run python bench/build_server_pack.py --version 1.0.3 --output-dir /tmp/server-pack
   ```

3. Test the pack against the server. Upload the pack to a separate GitHub release
   tagged `forgotten-worlds-1.0.3`, with `--prerelease --latest=false`. This tag
   does not start the launcher build workflow or replace its latest release.
4. Copy the generated `forgotten-worlds.json` to `modpacks/forgotten-worlds.json`
   and commit it to `main` **after** the release asset is available. The JSON pins
   the download URL, exact size, SHA-256, pack version and Minecraft/Fabric target.

No launcher version bump or launcher tag is needed for these steps. Keep release
assets immutable. Increasing the pack version also permits intentional mod
rollbacks without rolling back the channel version itself.

## What updates preserve

The updater reuses the existing instance and transactional file update engine.
Only verified pack-managed mod/resource/shader artifacts are replaced. Existing
configuration and player data are preserved; new defaults are added only when
absent. Deleted bundled mods stay deleted, disabled mods stay disabled, and custom
mod identity conflicts stop the update before modifying the instance. A failed or
cancelled commit restores touched files and the previous pack receipt.

The current updater requires the same Minecraft and exact Fabric loader target.
Changing that target is rejected before the instance is modified. GOML and Polymer
are installed on the server only and are deliberately excluded from the client pack.
