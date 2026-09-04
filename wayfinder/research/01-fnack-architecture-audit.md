# fnack plugin architecture + Subsonic plugin — ground-truth audit

Ticket: 01-audit-fnack-architecture (research)
Status: resolved
Sources: fnack `origin/main` @ `4962657` (v0.3.1) via `git show origin/main:<path>`;
fnack-plugins clean checkout of `main` (HEAD `4f0bc4b`). NOTE: the fnack-plugins
checkout advanced during this session (canonical manifests now declare fuller
permission sets); re-verify before executing.

## Plugin API (fnack origin/main v0.3.1)

- `plugins/base.py`: `PluginBase(ABC)` exists. `PluginManifest` dataclass has
  exactly: id, name, version, type, api_version, entry_point, min_core_version,
  author, description, homepage, permissions, settings_schema, ui, dependencies,
  trust_level. **No `actions`, no `capabilities` fields** — an unknown JSON key
  raises `TypeError` (`PluginManifest(**raw)`), so manifests carrying
  `capabilities`/`actions` FAIL to load on current core.
- All 15 typed interfaces exist: ServerExtensionPlugin (`register_routes(self,
  blueprint) -> None`), RecommendationPlugin (`recommend_for_artist`,
  optional `recommend_similar_tracks(track_id)`), MetadataProviderPlugin,
  DownloaderPlugin, FingerprintPlugin, ScanTriggerPlugin (`trigger_scan`,
  optional `test_connection`), LibraryTaskPlugin, VPNPlugin, UIExtensionPlugin,
  EventHookPlugin, LyricsProviderPlugin, StorageBackendPlugin, AuthProviderPlugin
  (`authenticate(request_headers)`), LibrarySourcePlugin, ConflictResolverPlugin.
- `plugins/context.py` facades: library, settings, events, http, fs, ui, jobs,
  log — exactly the brief's list, nothing more.
  - `LibraryContext`: get_track, get_album, get_artist, list_missing_tracks,
    list_artists, list_albums(artist_id=None, limit=500), list_tracks(album_id=None,
    limit=1000), get_setting/set_setting, get_api_key() -> str (`''` if unset),
    update_track_status, mark_caution. All return plain dicts. **No
    get_or_create_api_key()**, no search, no genres, no cover-art bytes/paths
    (album dicts have `cover_url` only), no starred/ratings/playlists, no
    music-folders, no scan trigger.
  - `http`: plain `requests.Session()` with UA header only — **no default
    timeout, no `network` permission enforcement**.
  - `fs`: downloads_dir/music_dir from env; open_download_path gated by
    `filesystem:downloads`; open_data_path unrestricted.
  - `log`: `logging.getLogger("fnack.plugin.<id>")`.
- `plugins/__init__.py`: `PLUGIN_API_VERSION = "1.0.0"`; `VALID_TYPES` set of 15
  type strings. **No capability registry, no `fnack.plugin_api` module, no
  capability constants** (`server.extension` etc. are ad-hoc strings in
  fnack-plugins manifests only; core ignores them / chokes on the key).
- `plugins/manager.py`: manifest validation requires id/name/version/type/
  api_version/entry_point; unknown `type` values → warning then load;
  compatibility via `api_version` caret shorthand + `min_core_version`;
  lifecycle on_load → on_enable → on_disable → on_unload +
  on_settings_changed (settings REST only); `call_safe` wraps every plugin call
  in gevent timeout (DEFAULT_HOOK_TIMEOUT=10s, DOWNLOAD=600s), catches
  BaseException, auto-disables after 5 consecutive failures.
- `plugins/api.py` + app.py wiring: server_extension blueprints register at
  boot against a fresh Flask blueprint mounted at root (`/rest/*`); enable/
  disable later does not (un)register routes. **No manifest `actions`
  mechanism exists anywhere.**
- Permission enforcement reality: only `FSContext.open_download_path` enforces
  `filesystem:downloads`. `network`/`settings` are NOT enforced in code
  (AUTHORING.md overstates). fnack-plugins README references
  `plugins/essential.py` `ESSENTIAL_PLUGINS` — **does not exist on origin/main**.

## Canonical Subsonic plugin (fnack-plugins, current main)

- plugin.json (verified directly this session): id `fnack.subsonic`, name
  "Subsonic API", version 1.0.0, type [server_extension], api_version ^1.0,
  min_core_version 0.2.0, permissions **[settings, library:read,
  filesystem:music]**, settings_schema [{enabled boolean default false}],
  trust_level official, capabilities **[server.extension]**. The `capabilities`
  key would TypeError under current core's strict manifest parser (drift —
  vendored mirror in fnack has permissions [settings] and NO capabilities key
  and is what core actually loads today).
- plugin.py (151 lines, `SubsonicPlugin(ServerExtensionPlugin)`): JSON-only
  responses; no XML. Envelope `{subsonic-response:{status,version:"1.16.1",…}}`;
  errors always HTTP 200 + `status:"failed"` + error code/message. Auth
  `_auth_ok`: `context.library.get_api_key()`; empty key → open (zero-auth);
  else `p == key` or `t == md5(key+salt)` (no u/c/v/f checks, no enc: hex, no
  apiKey param). Routes registered for GET+POST on both `/rest/<name>` and
  `/rest/<name>.view` — unconditionally (enabled flag not gating, noted in
  code comment as pre-existing behavior).
- Endpoints today: ping, getLicense (returns type fnack + validUntil), getArtists
  (ar- ids, letter-bucketed index), getAlbumList2 (al- ids, songCount 0),
  getAlbum (songs tr-), getSong, stream (raw send_file, no Range/transcode,
  mimetype map for flac/opus/ogg/mp3/m4a/aac/wav), getCoverArt (always error 70
  "not yet indexed"), getScanStatus + startScan (static stub). Missing: search3,
  getIndexes, getMusicFolders, getArtist, getSimilarSongs/2, getArtistInfo/2,
  download, XML, genres, playlists, scrobble.
- Errors used: 40 wrong auth, 70 not found/cover. Malformed id (non-int after
  prefix) → uncaught ValueError → 500.
- Bundled mirror vs canonical drift (plugin.py): canonical removes
  on_load/_render_settings_tab ("settings via standard schema modal; custom
  settings_tab card retired"), bundled still has them. Manifest drift: bundled =
  permissions [settings], no capabilities key.

## Release / test conventions

- fnack-plugins canonical; package via `python3 package_plugins.py` (zips each
  plugin → dist/, sha256, regenerates index.json; download URLs point at GitHub
  release `v<version>`); parity guard `python3 tests/test_manifest_index_parity.py`
  (currently passes: 18 plugins). No CI workflows in fnack-plugins; fnack CI
  runs `tests/run_smoke_test.py` then builds/publishes ghcr image on main + tags.
- Release workflow (fnack wayfinder "Decisions so far"): edit in fnack-plugins →
  package_plugins.py → commit/push fnack-plugins → vendor files into
  fnack/bundled_plugins/ → tag core release. Do not push directly to fnack main;
  use branches + PRs (fnack's own plugin-architecture flow merged via PRs).

## Brief assumption vs reality (highlights)

- §3 facade list: matches. ServerExtensionPlugin: matches.
- §4/§21/§22 `actions`/`capabilities` in manifest + capability registry +
  capability constants: **do not exist in core**. Manifests with those keys fail
  to load on v0.3.1. Forward-compat warnings exist only for unknown `type`
  strings.
- §9 get_or_create_api_key(): **absent** — only get_api_key() exists.
- §5 enforced permissions: only filesystem:downloads; network/settings declared
  but unenforced (AUTHORING overstates); unused-permission warnings: absent.
- §10 library facade: get/list methods match; search/cover-art-bytes/genres/
  scan/all-tracks enumeration absent (API gaps).
