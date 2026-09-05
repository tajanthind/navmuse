# fnack.subsonic — Subsonic/OpenSubsonic server extension (upgraded)

Version 1.1.0 · api_version `^1.0` · type `server_extension` · capability
`server.extension` · permissions `settings`, `library:read`, `network`

Exposes fnack's music library as a **Subsonic / OpenSubsonic-compatible REST
server** for Symfonium, DSub, Sublime Music, and other clients, with an
**optional AudioMuse-AI sonic-similarity integration** inside the same plugin
(default off). This folder mirrors the canonical fnack-plugins layout
(`plugins/<id>/`) and is the staging copy built per the decision-complete plan
in [`wayfinder/map.md`](../../wayfinder/map.md); it is committed to
`tajanthind/navmuse` and intended to be copied into `tajanthind/fnack-plugins`
as the real PR (see the map's implementation-home ticket).

## Endpoints

Wire contract verified against the classic spec + OpenSubsonic docs
(research/03). All endpoints answer on `/rest/<name>` and `/rest/<name>.view`,
GET and POST. XML is the default format; `f=json` (or `format=json`) returns
JSON. Every response carries the OpenSubsonic envelope attributes
(`type`, `serverVersion`, `openSubsonic: true`).

Implemented:

- ping, getLicense, getMusicFolders, getIndexes, getArtists, getArtist,
  getAlbum, getMusicDirectory, getAlbumList2, getSong
- search3 (local-library substring search; empty query returns data per OS)
- getCoverArt (transitional local-cover heuristic — see Limitations)
- stream, download (raw files; HTTP Range via Flask `send_file(conditional=True)`)
- getSimilarSongs, getSimilarSongs2 (AudioMuse-first, fnack-fallback)
- getArtistInfo, getArtistInfo2 (minimal valid; no AudioMuse artist-info)
- getScanStatus, startScan (honest no-op — fnack exposes no scan trigger to
  server extensions)
- getOpenSubsonicExtensions (advertises `apiKeyAuthentication`, `formPost`)

Auth follows the classic spec against fnack's M2M API key: `u`+`p` (plain or
`enc:` hex), `u`+`t`+`s` (`md5(key+salt)`), or the OpenSubsonic `apiKey` param.
Zero-auth (open) only while no key is configured; fnack auto-creates a key at
startup on current core, so `/rest/*` is normally key-gated. Error codes 40/70
plus OS 43 (conflicting schemes); errors travel as HTTP 200 + failed status.

### Username / password for Subsonic clients

fnack has **no user accounts** — there is a single M2M API key, and that key
is the only credential `/rest/*` knows. Point any Subsonic app
(Symfonium / DSub / Sublime Music / Tempo / …) at `http://<fnack-host>:4688/rest`
and set:

- **Username**: anything (it is accepted but not checked — e.g. `fnack`).
- **Password**: fnack's M2M API key — read it from fnack's settings
  (`GET /api/settings` → `api_key`, or the Settings page).
- **Protocol**: Subsonic (OpenSubsonic is supported too); **HTTP** or HTTPS.

Clients that offer token auth (`t`/`s`) also work against the same key.
If the key is ever cleared, the API falls back to open (fnack's zero-auth
default) until the next key is generated.

## AudioMuse-AI settings

| Key | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | boolean | `true` | Master switch for the Subsonic server |
| `audiomuse_enabled` | boolean | `false` | Enable the AudioMuse integration (off = zero AudioMuse behavior) |
| `audiomuse_base_url` | string | `""` | e.g. `http://192.168.1.10:8000` |
| `audiomuse_api_key` | secret | `""` | Bearer token (encrypted at rest); empty = no header |

When `audiomuse_enabled` is false there are no AudioMuse calls of any kind.
When enabled, `getSimilarSongs`/`getSimilarSongs2` call
`GET {base}/api/similar_tracks?item_id=<tr-id>&n=<count>` (with Bearer when a
key is set) and translate the response into Subsonic `<song>` records —
AudioMuse-first, fnack-fallback: disabled / unreachable / timeout / 4xx-5xx /
invalid JSON / unknown rows all fall back to the smallest valid response, never
a server error (fnack auto-disables plugins after repeated failures; the
integration must fail soft). The translation layer lives in
`audiomuse_client.py` so AudioMuse field names never reach the route layer.

A "Test AudioMuse-AI connection" button is provided through the manifest
`actions` mechanism (method `test_audiomuse_connection`).

## Limitations (verified, not hidden)

- **Cover art**: fnack's `LibraryContext` does not expose cover-art
  bytes/paths (core API gap — wayfinder ticket 16). `getCoverArt` uses a
  transitional heuristic: it looks for `cover.jpg`/`folder.jpg`/… beside the
  first track of the referenced song/album/artist. A narrow core facade
  addition (e.g. `library.get_cover_art(...)`) is the clean fix and should
  replace this when it lands.
- **No transcoding**: `stream`/`download` serve the original bytes (no ffmpeg
  in the container). `maxBitRate`/`format` params are accepted and ignored.
- **search3** filters over full-library scans (`list_tracks(limit=100000)`
  etc.) — correct but not indexed; large libraries are slower.
- **Artist info**: fnack holds no artist bios/images; `getArtistInfo/2`
  return a minimal valid structure (AudioMuse has no artist-info endpoint, so
  the integration is similarity-only by design).
- **Scan**: `startScan` is an honest no-op (no scan capability on the facade).
- **Formats**: XML + JSON implemented; `jsonp` not implemented.

## Manifest notes

- `api_version: ^1.0` — fnack plugin API 1.x.
- `min_core_version: 0.3.21` — needs the core that enforces manifest
  permissions, supports `capabilities`/`actions`, encrypts secrets at rest,
  and auto-creates the M2M key.
- Permissions declared are exactly what the code touches:
  `settings` (settings_schema/context.settings), `library:read` (all library
  reads), `network` (`context.http` for AudioMuse). No `filesystem:*` —
  streaming serves library-provided paths directly via `send_file`, matching
  the previous plugin, so no fs facade permission is exercised.
- `capabilities: ["server.extension"]` (real constant in
  `fnack.plugin_api.capabilities`).
- `actions`: `test-audiomuse-connection` maps to
  `SubsonicPlugin.test_audiomuse_connection()`.

## Development

Tests are plain-python (unittest, no pytest, no network) and run against a
stub fnack context — see `tests/test_subsonic_plugin.py`:

```bash
/home/tajanthind/fnack/.venv/bin/python tests/test_subsonic_plugin.py
```

(navmuse staging note: fnack/fnack-plugins are read-only ground truth; the
plugin is implemented and tested here, then vendored into fnack-plugins by an
execution session.)
