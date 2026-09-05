# Audit the current fnack plugin architecture + the bundled Subsonic plugin inventory

Type: research
Status: resolved
Blocked by: (none)

## Question

Establish the exact current state of the fnack plugin architecture and the
existing Subsonic plugin, as ground truth for every downstream decision in this
map. The brief (§2, §7) forbids assuming paths or APIs.

Specifically:

1. Current plugin API on fnack `main`: which concrete typed interfaces exist in
   `plugins/base.py` (does `ServerExtensionPlugin` exist, what does
   `register_routes(self, blueprint)` require)? What does `PluginContext`
   expose today — exact facades and method signatures on the library facade
   (`get_track`, `get_album`, `get_artist`, `list_artists`, `list_albums`,
   `list_tracks`, `get_api_key`, `get_or_create_api_key`, …), plus
   `context.settings`, `context.http`, `context.events`, `context.fs`,
   `context.ui`, `context.jobs`, `context.log`?
2. Manifest schema + capability registry: exact fields validated
   (`id/name/version/type/api_version/entry_point/min_core_version/permissions/
   settings_schema/ui/actions/dependencies/trust_level/capabilities`), the
   `type` enum, and which capability constants exist (is there a
   `server.extension`, `recommendation`, or `similarity` capability?). How are
   unknown capabilities handled?
3. Permission model: which permission strings are enforced (network, settings,
   filesystem:…), and how undeclared access is rejected.
4. Lifecycle: `on_load/on_enable/on_disable/on_unload/on_settings_changed`
   hooks and the manager's timeout/auto-disable wrapping.
5. The Subsonic plugin inventory: where the canonical plugin lives
   (`fnack-plugins/plugins/fnack.subsonic` vs the `fnack/bundled_plugins`
   mirror), its current `plugin.json`, and exactly which endpoints are
   implemented (ping, getLicense, getArtists, getAlbumList2, getAlbum, getSong,
   stream, getCoverArt, getScanStatus/startScan, …), response format (JSON
   only? XML?), envelope/error conventions, auth semantics (u/p, t/s token,
   api-key, zero-auth open), ID mapping scheme (ar-/al-/tr- prefixes), stream
   behavior (range handling, mimetypes), and what is NOT implemented yet
   (XML, search3, getIndexes, getMusicDirectory, getMusicFolders, download,
   getSimilarSongs/2, getArtistInfo/2, …).
6. Any API gaps the full Subsonic surface needs (search over the library,
   cover-art bytes, music-folder listing, file/range serving) — i.e. what the
   current facade cannot express, so the map can decide minimal core additions.
7. Tests/lint/CI conventions in both repos and how a plugin change ships
   (fnack-plugins canonical → package → vendor into fnack bundled_plugins →
   tag) per the repo READMEs and fnack `wayfinder/map.md`.

## Resolution

RESOLVED (research) — full findings in
`research/01-fnack-architecture-audit.md`. **Corrected after pulling the live
AUTHORING.md** (fnack `main` is v0.3.21 @ `b07916be`, not the stale local
clone v0.3.1): highlights that drive this map:

- fnack core v0.3.21 matches the brief §3 surface AND the §4/§21/§22 model:
  `PluginManifest` has real `actions` + `capabilities` fields; a public SDK
  `fnack/plugin_api/` exists (capabilities.py exports SERVER_EXTENSION etc.,
  contracts.py validates declared capabilities → skip-with-warning); the
  manager dispatches manifest actions via `POST /api/plugins/<id>/action/
  <action_id>`.
- Permissions ARE enforced and fail-closed: `context.http` is None unless
  `network` declared; `context.settings` requires `settings`; library reads
  need `library:read`, writes `library:write`; fs gates exist. Declared-but-
  unused permissions are warned. (The earlier v0.3.1 audit's "not enforced"
  finding is obsolete.)
- `LibraryContext` (live): get_api_key() AND get_or_create_api_key() (via
  library:write), the §10 get/list methods, search_albums/search_tracks
  (Deezer live), verify helpers, job ops. Real API gaps remain: no cover-art
  bytes/paths (only cover_url), no local-library full-text search, no genres,
  no starred/ratings/playlists/music-folders, no scan trigger.
- Canonical `fnack.subsonic` (fnack-plugins @ 4f0bc4b) == bundled mirror on
  live main (drift gone): JSON-only first-cut endpoints
  (ping/getLicense/getArtists/getAlbumList2/getAlbum/getSong/stream/getCoverArt/
  getScanStatus/startScan), `ar-/al-/tr-` ids, permissions [settings,
  library:read, filesystem:music], capabilities [server.extension]; no
  search3/similarSongs/artistInfo/download/XML. Zero-auth-open only when no
  M2M key exists — and fnack now auto-creates the key at startup.
- Release flow: fnack-plugins canonical → package_plugins.py → parity guard →
  commit/push → vendor into fnack bundled_plugins → tag core release; fnack
  tests: tests/run_smoke_test.py + tests/architecture/. `plugins/essential.py`
  (live) excludes fnack.subsonic (marketplace-official, not Docker-essential).
