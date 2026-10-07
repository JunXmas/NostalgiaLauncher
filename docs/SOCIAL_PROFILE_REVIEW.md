# Friends avatars and profile preview — 2026-10-07

Source changes live on `preview/glass-review` and the backend preview branch. No installer, tag, draft release, production deployment or paid-feature activation is included. Images are supplied separately in chat, outside Git and release assets.

## Interaction

Friends, incoming requests, the chat header and the Google account corner now show avatars. The default is the verified Google picture; missing pictures use initials. The profile editor also supports a published Minecraft skin face or initials. Clicking a friend's avatar or the chat profile action opens a centered mica popup. The owner opens the same popup through the account corner or Hồ sơ của tôi.

Profiles show a short bio, online status, authoritative membership badge, avatar frame/banner decor, a rotatable 3D skin and up to three manually selected favorite modpacks/bản chơi. The existing palette, glass components and inertial scroll are reused. Names in the friend list retain a compact badge symbol; full badge text belongs in the profile. Large-font/small-window layouts retain scrolling and fixed actions.

## Sharing and rights

Basic profile editing works with Google-only/free accounts even while Plus is paused. Skin and modpacks are opt-in: the owner selects a skin from the existing local library and chooses which installed instances to display. Publishing makes a normalized copy, not a change to the Microsoft/Ely.by account or the in-game skin. Existing skin/cape uploads remain unchanged. On a new machine, previously published skin and pack labels are retained when editing the bio.

Only the owner or accepted, unblocked friends can read a profile. Pending requests see an avatar but do not gain full-profile access. Blocking, friend removal or session reset clears the open local profile. Late replies cannot restore a closed profile. Profiles expose no Google sub/email, Minecraft credentials, local paths, friend code, session secrets or automatic play history.

Nondefault frames and banners use the existing Pro/Max/Ultimate membership boundary. Paid badges are derived by the backend, respect the existing hide-badge preference and disappear when entitlement is inactive/revoked/paused. Client-supplied badge/paid fields are rejected. Release runtime and backend flags remain paused; paid examples in screenshots use fixtures.

Cosmetic in this preview means launcher profile decoration. It does not implement in-game capes, hats or equipment. Favorite packs are manually curated display labels, not automatic usage statistics, official catalog verification or a one-click download feature.

## Performance and backend

Google image URLs are limited to approved HTTPS Googleusercontent hosts. Skin uploads are normalized to 64×64, and an 8×8 composited face is used for friend polling. Indexed PNGs are converted before composing the hat layer. Minecraft avatar faces use nearest-neighbor sampling; Google photos use smooth sampling.

Friend polling reads only avatar fields with D1 `json_extract`, avoiding full skin/bio/pack documents. Detailed skin is fetched on profile open, decoded, cached under a SHA256 filename, and capped to 48 stored public skin textures. The existing 3D renderer uses a single worker with bounded frame/atlas caches and renders the visible profile only. The model preserves the original 1:2 skin viewport ratio.

New D1 tables are additive: `service_avatars` and `public_profiles`. New routes are `GET /v1/profiles/{account_id}` and owner-only `POST /v1/profiles/me`. The old paid `/v1/profile` route keeps its existing behavior. See backend `account-service/PUBLIC_PROFILES.md` before an eventual deployment; schema migration and production Google deployment have not been executed.

## Verification

- Complete client suite: 1,465 passed, 7 skipped, 1 deselected.
- Full backend workerd/D1: 29 passed; final malformed pack-row guard additionally checked by the three passing profile integration cases.
- Native Qt/OpenGL and API/architecture/convention group: 31 passed, including the indexed-PNG hat-layer regression.
- Native profile flow covers opening the right friend, ownership controls, skin opt-in/removal, unchanged Minecraft accounts/files, centered popup, stale replies and corrupt image handling.
- Existing skin library/3D regression group: 11 passed.
- Ruff checks and formatting pass (530 files); mypy passes for 278 source files. Dependency lock and whitespace checks pass.

Four actual Qt/OpenGL screenshots show friends avatars, a profile, the editor and a 1024×600 window with 150% font size. The final capture reports no Qt/QML warnings. Accounts, chat, entitlements and published profile data are controlled fixtures; this is not proof of a deployed Google service or a real paid membership.
