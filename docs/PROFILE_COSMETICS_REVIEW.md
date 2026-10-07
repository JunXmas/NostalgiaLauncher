# Profile cosmetic artwork review

The existing colored avatar borders and profile gradients now use the approved
Amethyst, Grove and Eclipse artwork: transparent avatar frames plus matching
landscape banners. Frames appear in accepted friend rows, chat headers and
profiles. The editor shows three responsive artwork cards and a live header
preview, with a separate original-appearance option.

Grove retains the service ID `emerald`; Eclipse retains `amber`. Existing saved
profiles and backend validation remain compatible without a migration.

## Permissions and scope

Everyone can browse the local artwork. Selecting a locked card changes only
`previewDecor`, while saving uses the entitled selection. Canceling restores the
saved profile. Applying a set still requires the existing authoritative
Pro/Max/Ultimate backend check, including active membership and the paid-feature
flag. Modifying local client artwork does not grant a saved/shared cosmetic or
other service rights. Assets delivered to a desktop client remain extractable.

Paid release flags and payment gateways remain disabled. No production deployment,
migration, version bump, installer build, tag or release was made. Review captures
remain outside Git and release assets. Existing Microsoft/Ely.by skin operations
are unchanged; the profile still uses the existing opt-in skin and face flow.

## Rendering

Six production PNGs are packaged through the existing QML directory inclusion.
Frames have a transparent center and exterior. Asynchronous, cached images cap
decoded frames at 384 px and banners at 1536 px; hidden components clear their
sources. Only pointer/press transitions animate, respecting reduced motion.
No continuous decoration animation, new renderer or dependency was introduced.

Captured alpha masks keep GPU-rendered photos/banners rounded. This also fixes
the existing avatar mask that hid loaded photos. The software renderer displays
the image without the shader mask, so its image corners can appear rectangular.

## Verification

- 36 OpenGL/client tests pass: cosmetic preview/save/cancel, actual rendered
  pixels, asset alpha, bounded image sizes, source cleanup, profiles, friends,
  skin 3D, disabled release runtime, profile parsing and repository conventions.
- 7 software-renderer tests pass, including actual image pixels and paused runtime.
- 8 workerd/D1 backend profile/security cases pass, including spoofed decor,
  paused/expired/revoked rights, friendship and bound-session checks.
- Ruff, formatting, source mypy, lockfile and whitespace checks pass.
- Actual Qt captures cover all three sets, accepted friend avatars, opt-in skin,
  and a 1024×600 window with 150% text. QML warning capture is empty. Accounts,
  permissions, favorite packs and chat in screenshots are controlled fixtures.

These checks exercise the UI and local service integration. They do not claim
production OAuth/payment verification or a hardware FPS benchmark.
