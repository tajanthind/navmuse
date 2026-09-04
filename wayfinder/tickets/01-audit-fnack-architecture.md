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
`research/01-fnack-architecture-audit.md`. Highlights that drive this map:

- fnack core v0.3.1 (`origin/main` @ 4962657) matches the brief's §3 surface:
  `PluginBase(ABC)`, all 15 typed interfaces, `ServerExtensionPlugin.register_routes`,
  and the 8 `PluginContext` facades — but **no capability registry, no
  `capabilities`/`actions` manifest fields, and no `fnack.plugin_api` module**.
  `PluginManifest(**raw)` raises `TypeError` on unknown keys, so the canonical
  fnack-plugins manifests (which carry `capabilities`) cannot load under current
  core — only the vendored mirror (no `capabilities` key) loads. This is live
  ecosystem drift (marketplace ahead of core) and must be resolved by the
  implementation session (see ticket 04).
- `LibraryContext` has get_api_key() (no get_or_create_api_key), the
  get/list methods the brief lists, but **no search, no genres, no cover-art
  bytes, no scan trigger, no all-tracks enumeration** → those are real API gaps.
- Permission enforcement is partial: only `filesystem:downloads` is enforced;
  `network`/`settings` are declared-but-unenforced (AUTHORING.md overstates).
- Canonical `fnack.subsonic` today: JSON-only, ~10 first-cut endpoints
  (ping/getLicense/getArtists/getAlbumList2/getAlbum/getSong/stream/getCoverArt/
  getScanStatus/startScan), `ar-/al-/tr-` ids, zero-auth-open when no key, raw
  streaming, cover art always error 70, no search3/similarSongs/artistInfo/
  download/XML. Routes registered unconditionally at boot for enabled plugins.
- Release flow: fnack-plugins canonical → package_plugins.py → commit/push →
  vendor into fnack/bundled_plugins → tag core release; tests: plain python
  parity test in fnack-plugins, `tests/run_smoke_test.py` in fnack.
