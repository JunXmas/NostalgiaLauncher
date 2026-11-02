# Premium authorization hardening preview — 2026-10-07

The source changes remain on `preview/glass-review` and the backend preview branch. No installer/version bump/tag/draft/release/production deployment is included. Payments and paid runtime flows remain disabled.

## Result

New Google logins pin a per-session Ed25519 public key at login start. The private seed stays in RAM or the existing approved OS credential vault, alongside the bearer. The launcher sends a signature for the exact request method, URL, bearer hash and actual body hash, with issue time and a fresh nonce. Backend uniqueness claims reject concurrent replay; changing the body/method/URL/token or using another key fails. A bearer copied without its matching signing key cannot use a bound session. There is no key-rebinding endpoint authorized by the bearer alone.

Social, payment, repair, server and host modpack-sync adapters reuse that proof. CDN/game downloads and Free guests do not sign or send a Premium bearer. The existing secure-store interface restores the paired token/key, refuses plaintext backends and retains RAM-only behavior when no approved vault is available. Logout/reset clears the memory key. Google login remains in the browser; no Google password/private OAuth secret is added to the launcher.

The backend requires both active entitlement and matching unrevoked plan metadata. An expired/revoked/missing ledger no longer produces Premium or visible paid decor. The shared active-session pointer is also checked by the relay authorizer. Paid mutation predicates are included in the D1 write itself. Legacy sessions without a pinned key keep Free access but must sign in again to use Premium.

Repair apply grants are owner/session/scan-bound and consumed once. Browser preview download tickets last 60 seconds, are pinned to target/version/object and permit one successful claim. A short-lived browser link can still be transferred once; a downloaded build is not DRM-protected. If a repair fails after consuming its grant, request a new plan; local backups and undo remain available.

One synchronized modpack host reservation per account is enforced atomically, including simultaneous starts. It follows the live room/socket/Google session, allows a new-machine takeover and rejects cleanup from the old session. Free guests still download from their Premium host. Game connections are not shortened by this reservation; existing snapshot expiry remains four hours. Server receipt time allows bounded slow uploads while client-supplied timestamp headers cannot relax freshness.

## Security limits and rollout

This is an application possession protocol, not hardware attestation or a claim of standards-compliant DPoP. A person controlling their machine may copy both the token and private key, modify local UI/code, start public Java server files, or redistribute already-received data. Server-side checks protect the project's own services. One active session/server/sync reservation does not identify physical hardware or make local Premium features unbypassable.

The backend needs the additive schema and matching account/relay/authorizer versions deployed together. The authorizer must remain accessible only through service bindings, with routes/workers.dev disabled. Historical entitlement-only entries must be reconciled against verified billing records rather than upgraded from client flags. No production migration/deployment/payment activation was performed; production Google/payment testing is still pending. Detailed rollout instructions live in backend `account-service/PREMIUM_HARDENING.md`.

## Verification

- Complete launcher suite: **1,469 passed, 7 skipped, 1 deselected**.
- Focused social, secure-store, payment, repair, server, HTTPS and architecture/convention group: **120 passed**.
- Ruff checks/formatting pass (533 files); mypy passes for 280 source files. Dependency lock and whitespace checks pass.
- Complete backend workerd/D1/R2 suite: **37 passed**.
- Separate integration uses the actual Python launcher signer against workerd/D1 account and relay APIs: valid request accepted, replay rejected, and Free guest download bytes match.
- Native Qt/OpenGL social/profile/release-runtime/skin regression group: **24 passed**.

These automated checks are not a comprehensive independent penetration test or evidence of production deployment.
