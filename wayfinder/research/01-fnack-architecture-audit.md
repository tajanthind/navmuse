# fnack plugin architecture + Subsonic plugin — ground-truth audit

Ticket: 01-audit-fnack-architecture (research)
Status: resolved
Sources: **live GitHub** `tajanthind/fnack` `main` @ `b07916be` (v0.3.21,
security-enforced-permissions + secret-at-rest merged, PR #42) and
`tajanthind/fnack-plugins` `main` @ `4f0bc4b`, fetched read-only via the GitHub
API on 2026-09-04. The up-to-date author guide is pinned at
`reference/AUTHORING.md` (fnack main commit `e899848cdd`).

> Correction note: an earlier version of this audit was grounded on the LOCAL
> clone's stale `origin/main` (fnack v0.3.1 @ 4962657). Live `main` is
> v0.3.21 and materially newer — permissions are enforced, the manifest now
> supports `capabilities` and `actions`, and `fnack.plugin_api` exists. The
> findings below are the corrected, live-main facts.

## Plugin API (live fnack main v0.3.21)

- `plugins/base.py`: `PluginBase(ABC)` exists. `PluginManifest` dataclass now
  includes `actions: list[dict]` (imperative commands rendered in the settings
  modal; each `id` maps to a snake_cased method invoked via
  `POST /api/plugins/<id>/action/<action_id>`) AND `capabilities: list[str]`
  (unknown IDs warn forward-compatibly; omitted → derived from `type`). Fields:
  id, name, version, type, api_version, entry_point, min_core_version, author,
  description, homepage, permissions, settings_schema, ui, actions,
  dependencies, trust_level, capabilities.
- All 15 typed interfaces exist (ServerExtensionPlugin.register_routes,
  RecommendationPlugin.recommend_for_artist + recommend_similar_tracks, etc.).
- `plugins/__init__.py`: `PLUGIN_API_VERSION = "1.0.0"`, `VALID_TYPES` set of
  15. A **public SDK** exists at `fnack/plugin_api/` (`capabilities.py`,
  `contracts.py`, `providers.py`, `errors.py`, `models.py`, `context.py`,
  `events.py`, `version.py`) — `capabilities.py` exports constants incl.
  `SERVER_EXTENSION = "server.extension"`, `ARTIST_INFO = "artist.info"`, etc.;
  `contracts.py` is the single source of truth mapping capability → required
  interface method(s), and the manager SKIPS (with a warning) any declared
  capability the plugin doesn't implement.
- `plugins/context.py`: 8 facades; every facade enforces DECLARED manifest
  permissions via `PermissionChecker` (fail closed):
  - `context.http` is a `requests.Session` **only if `network` declared —
    otherwise it is `None`** (plugin gets a PermissionError-free hard None, so
    any AudioMuse HTTP work REQUIRES the `network` permission).
  - `context.settings.get/set/all` require `settings`.
  - `context.library` read methods require `library:read`; write methods
    (`set_setting`, `update_track_status`, `mark_caution`,
    `get_or_create_api_key`, job ops) require `library:write`.
  - `context.fs.open_download_path` requires `filesystem:downloads`;
    `open_music_path` requires `filesystem:music`.
  - Declared-but-unused permissions are surfaced as warnings (AUTHORING §2).
- `LibraryContext` methods (live): get_track, get_album, get_artist,
  list_missing_tracks, list_artists, list_albums, list_tracks, get_setting/
  set_setting, get_api_key ('' if unset), **get_or_create_api_key** (generates
  + persists via library:write), search_albums/search_tracks, get_album_info/
  get_track_info, queue_lidarr_grab, list_download_jobs, cancel_download_job,
  update_track_status, mark_caution, verify_audio_file,
  verify_download_acoustid. Gaps for a full Subsonic server remain: no
  cover-art bytes/paths (album dicts carry `cover_url` only), no genres/
  starred/ratings/playlists, no local-library full-text search (the
  search_* methods are live Deezer lookups), no music-folder concept.
- Startup (app.py module-level init, inside `with app.app_context():`):
  bundled plugins auto-install and are enabled by default EXCEPT
  `auth_provider`; `plugin_manager.load_all(enabled_ids=…)`; then
  server-extension blueprints are registered for every enabled provider in the
  **capability registry** (`capability_registry.providers(SERVER_EXTENSION)`) —
  only ENABLED plugins get `/rest/*` routes at boot. **An M2M API key is
  auto-created at startup** (`LibraryContext(...).get_or_create_api_key()`),
  so after first boot `get_api_key()` returns a real key (also surfaced via
  `/api/settings`); fnack's zero-auth model applies to human-facing pages —
  server-extension APIs are key-gated once the key exists.
- `plugins/manager.py`: `call_safe` gevent-timeout wrapper, auto-disable after
  5 consecutive failures (DEFAULT_HOOK_TIMEOUT 10s / download 600s); plugin
  lifecycle on_load/on_enable/on_disable/on_unload/on_settings_changed.
- `plugins/secret_store.py`: Fernet encrypt-at-rest for manifest `type:
  "secret"` settings; startup backfill encrypts legacy plaintext rows.

## Canonical + bundled Subsonic plugin (live, both now in sync)

- Canonical `fnack-plugins/plugins/fnack.subsonic/` == vendored
  `fnack/bundled_plugins/fnack.subsonic/` (verified byte-identical plugin.py
  on live main; the earlier local-clone drift is gone). Manifest v1.0.0:
  type [server_extension], api_version ^1.0, min_core_version 0.2.0,
  permissions **[settings, library:read, filesystem:music]**, settings_schema
  [{enabled bool default false}], capabilities **[server.extension]**. This
  manifest LOADS fine on live core (capabilities supported).
- plugin.py (151 lines, `SubsonicPlugin(ServerExtensionPlugin)`): JSON-only
  responses; no XML. Envelope `{"subsonic-response":{status:"ok|failed",
  version:"1.16.1",…}}`; errors HTTP 200 + status failed + code/message. Auth
  `_auth_ok`: `context.library.get_api_key()`; if empty → open (zero-auth);
  else accept `p == key` or `t == md5(key+salt)` (no u/c/v/f/apiKey checks,
  no enc: hex). Routes registered for GET+POST on `/rest/<name>` and
  `/rest/<name>.view` — at boot only if the plugin is enabled (capability
  registry); the manifest `enabled` checkbox is stored but NOT consulted by
  the plugin code.
- Endpoints today: ping, getLicense, getArtists (ar- ids, letter-bucketed),
  getAlbumList2 (al-, songCount 0), getAlbum (songs tr-), getSong, stream
  (raw send_file, no Range/transcode; flac/opus/ogg/mp3/m4a/aac/wav),
  getCoverArt (always error 70 "not yet indexed"), getScanStatus + startScan
  (static stubs). Missing: search3, getIndexes, getMusicFolders, getArtist,
  getSimilarSongs/2, getArtistInfo/2, download, XML, genres, playlists.
- Errors used: 40 wrong auth, 70 not found/cover. Malformed id → uncaught
  ValueError → 500 (fix planned in the upgrade).

## Release / test conventions (live)

- fnack-plugins canonical → `package_plugins.py` (zip+sha256+index.json) →
  parity guard `tests/test_manifest_index_parity.py` → commit/push → vendor
  into fnack `bundled_plugins/` → tag core release. fnack tests:
  `tests/run_smoke_test.py` + architecture tests under `tests/architecture/`
  (e.g. test_phase3_completion, test_essential_plugins). No lint config in
  fnack-plugins; fnack CI runs smoke test then docker publish.
- `plugins/essential.py` (live) is the authoritative Docker-essential set:
  {fnack.spotiflac, fnack.ytdlp, fnack.spotify, fnack.deezer-batch} —
  fnack.subsonic is NOT essential; it ships as a marketplace-installable
  official plugin (vendored mirror still present for older images/installs).

## Brief assumption vs reality (live main v0.3.21 — corrected)

- §3 facades + ServerExtensionPlugin: matches.
- §4/§21/§22 `actions`, `capabilities`, capability registry + constants:
  **now supported** (manifest fields, SERVER_EXTENSION constant, contract
  validation, actions dispatch endpoint). The brief's model is current.
- §5 permission enforcement: **now real and fail-closed** (network → http
  exists; settings; library:read/write; filesystem:*). Declared-but-unused
  warned.
- §9 `get_or_create_api_key()`: **exists** (library:write). fnack auto-creates
  the key at startup, so server-extension APIs are key-gated after first boot.
- §10 library facade: read/list methods match; search_albums/search_tracks are
  Deezer live searches, not local-library search; cover-art bytes, genres,
  scan-trigger and all-tracks enumeration still absent (API gaps).
- §14 secrets: `type: "secret"` settings are Fernet-encrypted at rest.
