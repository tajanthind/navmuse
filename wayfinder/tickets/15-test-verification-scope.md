# Decide the automated-test + verification scope

Type: task
Status: resolved
Blocked by: 01

## Question

What automated tests and verification procedures should the implementation
include (brief §24–§28)?

The brief prescribes the categories: Subsonic API endpoint tests (ping,
getMusicFolders, getArtists, getArtist, getAlbum, getMusicDirectory,
getCoverArt, stream, download, search3 + whatever the audit shows already
implemented); AudioMuse-disabled (zero HTTP calls, normal behavior);
AudioMuse-enabled (mock the exact real API shape from ticket 02 and verify
endpoint/method/params/auth/translation/getSimilarSongs/2 output);
AudioMuse-failure (timeout/connection/500/invalid-JSON/malformed → graceful
fallback); settings (defaults, secret not logged, stored via context.settings);
permissions (network/settings declared when used, none unnecessary);
architecture (no direct `models`/`db`/`app`/`services.*` imports). Plus a
documented live/manual smoke procedure (curl + a real Subsonic client where
practical) and the AudioMuse-off/on/unavailable runbooks.

This ticket fixes where tests live and how they run once ticket 01 reports the
repos' test conventions (fnack-plugins tests are plain-python parity checks;
fnack has a smoke test) — recommend: keep plugin tests inside fnack-plugins
mirroring its conventions, XML+JSON wire fixtures from ticket 03, mocked
AudioMuse per ticket 02, and never require a live AudioMuse to pass.

## Resolution

RESOLVED from audit (ticket 01) + wire spec (ticket 03) + AudioMuse research
(ticket 02) + brief §24–§28. Recorded test/verification plan for the
implementation session (nothing executes from this tracker):

- **Where**: plugin tests live alongside fnack-plugins conventions — plain
  python, no pytest, no network (mirroring `tests/test_manifest_index_parity.py`);
  fnack's `tests/run_smoke_test.py` stays the core smoke gate.
- **Subsonic API conformance**: XML + JSON fixtures per ticket 03 for the full
  endpoint set (ping, getMusicFolders, getArtists, getArtist, getAlbum,
  getMusicDirectory, getAlbumList2, getSong, getCoverArt, stream, download,
  search3, getSimilarSongs/2, getArtistInfo/2, getScanStatus); assert envelope
  attrs, error codes 40/70 (+ OS 41–44), format selection via `f`, id
  round-trips, and HTTP-200-failed error semantics.
- **AudioMuse disabled**: `audiomuse_enabled=false` → zero AudioMuse HTTP
  calls, zero DNS attempts, identical Subsonic behavior.
- **AudioMuse enabled**: mock `context.http` against the exact API shape from
  ticket 02 (`/api/similar_tracks`, Bearer header, item_id + n) → assert
  translation and getSimilarSongs/2 output.
- **AudioMuse failure**: mock timeout, connection error, HTTP 500, invalid
  JSON, malformed similarity response → graceful fallback (smallest valid
  response), no unhandled exceptions, no auto-disable spiral.
- **Settings/permissions/architecture**: defaults (enabled true,
  audiomuse_enabled false, audiomuse_base_url ""), secret never logged,
  settings via context.settings, permissions settings+network only, and a
  guard asserting the plugin never imports models/db/app/services directly.
- **Live smoke procedure** (documented, run in the user's real deployment):
  curl the §25 endpoint list against a running fnack; verify real stream
  playback with a Subsonic client where practical; AudioMuse-off, -on
  (real or realistically mocked instance), and -unavailable runbooks (§26–§28).
  Mark each as live-tested vs mock-tested vs unit-tested in the final report —
  never claim live verification that was only mocked.
