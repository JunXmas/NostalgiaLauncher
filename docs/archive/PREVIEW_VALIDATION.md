# Nostalgia Launcher preview — validation evidence

Source commit: 4226acf8599231453044e81e4d1d6f9161712bd5. Preview PR: https://github.com/JunXmas/NostalgiaLauncher/pull/4 . Stable v1.1.8 contains the Forge and original Minecraft model patches.

- ruff, ruff format and strict mypy passed.
- Local regression: 1,176 passed, 7 skipped, 2 deselected (network and a pre-existing process-tree/zombie assertion that also fails on baseline in this container).
- Full GitHub CI on Python 3.12, Python 3.13 and Windows updater passed: https://github.com/JunXmas/NostalgiaLauncher/actions/runs/37418958415 . No process test excluded in GitHub CI.
- 16 new critical storage/UI tests repeated ten times, all passed. Covered internal/external game directories, no overwrite, reused instance ID, ZIP traversal/symlink/case collision, corrupt trash isolation, keyboard onboarding/toggles, saved appearance/language, UI backup/restore/trash and persistent error/retry.
- Qt screenshots captured with local demonstration data at 1360×860 and 1024×600, text scale up to 150%; runtime capture had no QML messages. This is offscreen rendering, not a Windows interactive game test.
- Error details popup exercised with real Qt mouse events; clipboard retained the entire 6,043-byte diagnostic.
- All seven primary accents with white text measured at normal/hover: minimum contrast 5.8:1. This checks flat button color pairs, not a WCAG certification of the complete application.
- Wheel and sdist built. Linux PyInstaller bundle built, smoke test displayed `smoke ok` and exited 0.
- Ten bundled beacon/bookshelf model/texture resources compared byte-for-byte to the official Minecraft Java 1.20.1 client JAR and to the built preview bundle; all identical.
- Official Forge installer downloaded from maven.minecraftforge.net, 8,836,161 bytes; actual version.json ID `1.20.1-forge-47.4.23`, SHA256 `75cfcb11f60cc641dc83757c1357c08c9bdba255ec529feb115c5e89a59cf75a`.
- Actual Forge/modpack UI installation tests use local HTTPS and an installer stand-in. The launcher itself uses a direct connection that is unavailable in this development environment; the official JAR download used the environment proxy. End-to-end Internet installation and gameplay on the user's Windows machine remain to verify.
- Updater rejects prereleases, and version comparison confirms stable 1.1.8 does not downgrade preview 1.2.0rc1. Stable 1.2.0 will compare newer than 1.2.0rc1.

Release workflow (fresh checkouts, builds and packaged smoke tests): https://github.com/JunXmas/NostalgiaLauncher/actions/runs/37419266129 . Final release assets and checksums are attached to the prerelease.

Preview is kept outside main until the owner approves. Research is documentary and comparative; no Nostalgia users were surveyed or contacted.

All release workflow jobs completed successfully, including Windows/Linux/macOS arm64/x64 packaged smoke tests. Published stable and preview Windows installer downloads verified against SHA256SUMS. Preview Linux distribution uses ZIP/tar.gz/AppImage; native Debian/RPM prerelease packages are omitted to preserve correct upgrade ordering to a future stable package.
