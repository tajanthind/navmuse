# fnack: Subsonic/OpenSubsonic server-extension upgrade + optional AudioMuse-AI sonic-similarity

**Tracker**: local-markdown. Map = this file. Tickets = `tickets/NN-<slug>.md`,
one per decision, numbered from `01`, each carrying a `Type:` line
(`research` | `prototype` | `grilling` | `task`) and a `Status:` line.
Research findings = `research/<ticket-slug>.md`. Blocking is expressed in the
ticket body (`Blocked by: NN` line) since markdown has no native dependency
graph. Sessions claim a ticket by setting `Status: claimed` before work.

## Destination

A decision-complete implementation order for the brief
[`Brief_ Subsonic-API compatibility + optional AudioMuse-AI integration for fnack.md`](../Brief_%20Subsonic-API%20compatibility%20%2B%20optional%20AudioMuse-AI%20integration%20for%20fnack.md):
the bundled `fnack.subsonic` server-extension plugin becomes a real-world
Subsonic/OpenSubsonic-compatible `/rest/*` implementation (browse, search,
stream, download, similar-songs, artist-info) plus an **optional, default-off
AudioMuse-AI integration in the same plugin** supplying sonic-similarity
results — additive, single plugin, no second container, no startup dependency,
conforming to the current fnack plugin API (`api_version ^1.0`,
`ServerExtensionPlugin`, `PluginContext` boundary). When every decision on this
map is resolved, an execution session against `tajanthind/fnack-plugins` (and
the `fnack` bundled mirror) can run the brief without re-deciding anything.

## Notes

- Domain: self-hosted lossless music downloader/library manager (`fnack`;
  Flask + gevent + SQLite, zero-required-auth by default). Plugins load
  in-process; `PluginContext` is the compatibility boundary; plugins must not
  import `models` / `db` / the Flask app / core internals directly. Canonical
  plugin source = `tajanthind/fnack-plugins` (official repo; `index.json`
  catalog; `plugins/fnack.subsonic/` is the current Subsonic plugin), vendored
  into fnack's `bundled_plugins/` before core releases.
- **This tracker lives in `tajanthind/navmuse`.** `fnack` and `fnack-plugins`
  are READ-ONLY ground truth for sessions here: the user constraint is *do not
  make any changes to fnack or fnack plugins* — navmuse hosts only the chart,
  findings, and decisions; the feature executes later against the code repos.
- Ground truth: **live GitHub is authoritative.** fnack `main` is v0.3.21 (@
  `b07916be`, security-enforced permissions + secret-at-rest merged); canonical
  plugin source `tajanthind/fnack-plugins` `main` @ `4f0bc4b`; the up-to-date
  plugin-authoring doc is pinned at `reference/AUTHORING.md` (fnack main
  `e899848cdd`). The local checkouts under `/home/tajanthind/fnack` and
  `/home/tajanthind/fnack-plugins` may lag live `main` — treat them as hints
  only and re-verify against GitHub before executing. The brief is
  self-contained but the live repositories are authoritative over its
  assumptions; the Subsonic/OpenSubsonic specs are authoritative over wire
  behavior; AudioMuse-AI's running source is authoritative over its API.
  (The first audit of this map used the stale local v0.3.1 clone; it was
  corrected against live v0.3.21 — see research file 01.)
- Standing preferences (from the brief, hard constraints): one plugin, no
  second Subsonic/AudioMuse plugin; AudioMuse never bundled/installed/run by
  fnack; `audiomuse_enabled` defaults `false` with zero network behavior when
  off; additive integration preserving current behavior; AudioMuse-first,
  fnack-fallback semantics for similarity; do not invent endpoints, response
  fields, capability IDs, or credentials; use `context.http` /
  `context.settings` / library facade, never raw networking or ORM.
- Every session that works this map should consult `grilling` and
  `domain-modeling` skills; keep the shared glossary at `/CONTEXT.md`.

## Decisions so far

<!-- one line per resolved ticket; zoom the linked ticket for the detail -->

- [Audit the current fnack plugin architecture + the bundled Subsonic plugin inventory](tickets/01-audit-fnack-architecture.md):
  **Corrected against live fnack main v0.3.21** (@ b07916be; the first audit
  used a stale local clone at v0.3.1). Live core matches the brief's §3
  surface (PluginBase, 15 typed interfaces incl. ServerExtensionPlugin, 8
  PluginContext facades) AND the §4/§21/§22 model: real `capabilities` +
  `actions` manifest fields, `fnack/plugin_api/` SDK (SERVER_EXTENSION
  constant, contracts.py), permission enforcement that is fail-closed
  (context.http is None without `network`), secret-at-rest (Fernet), and an
  M2M key auto-created at startup. Library facade still lacks cover-art bytes,
  local-library search, genres, playlists, scan. Canonical fnack-plugins ==
  bundled mirror. Full findings in `research/01-fnack-architecture-audit.md`.
- [Research the real AudioMuse-AI HTTP API](tickets/02-research-audiomuse-http-api.md):
  Flask server port 8000, root routes; primary similarity endpoint
  `GET /api/similar_tracks` (item_id OR title+artist, n default 50) → JSON
  rows `{item_id,title,author,album,distance,…}`; M2M auth optional
  `Authorization: Bearer <API_TOKEN>`; artist similarity exists, artist-info
  does NOT; empty index → 503. Full findings in `research/02-audiomuse-http-api.md`.
- [Verify the Subsonic/OpenSubsonic wire contract for the endpoint set](tickets/03-verify-subsonic-opensubsonic-wire-contract.md):
  full 20-endpoint contract verified (params/results/envelope/error codes/ID
  semantics) — base `/rest/<name>`, `.view` optional, GET + OS formPost,
  required `u/p|t+s/v/c`, `f` default xml; envelope XML root or
  `{"subsonic-response":…}`; errors HTTP 200 + status failed; find in
  `research/03-subsonic-wire-contract.md`.
- [Decide capability + permission declarations for the upgraded Subsonic plugin](tickets/04-capability-permission-declarations.md):
  keep `capabilities: ["server.extension"]` (real constant + contract on live
  core — no invented IDs); declare permissions `settings`, `library:read`,
  `network` (context.http — mandatory for AudioMuse), and `filesystem:music`
  only if streaming moves behind context.fs; drop declared-but-unused perms;
  no `library:write`.
- [Decide the Subsonic ID strategy for the upgraded plugin](tickets/05-subsonic-id-strategy.md):
  preserve the prefixed-numeric contract (`ar-`/`al-`/`tr-` + stable numeric
  id) across every surface incl. coverArt/stream/download; no translation
  layer; malformed ids → error 70 not 500.
- [Decide /rest authentication semantics for the upgraded plugin](tickets/06-rest-auth-semantics.md):
  fnack auto-creates its M2M key at startup (v0.3.21), so /rest is normally
  key-gated; plugin reads it via get_api_key() and accepts classic `u`/`p`
  (plain + enc: hex) and `u`/`t`+`s` (md5(key+salt)) against it, plus the OS
  `apiKey` param and error codes 41–44; `u` not identity-checked; no parallel
  auth DB; zero-auth-open branch only before a key exists.
- [Decide the response format scope (XML + JSON)](tickets/07-response-format-scope.md):
  implement **both XML and JSON** — XML default per classic spec, `f=json`
  honored; AudioMuse translation layer stays format-agnostic.
- [Decide the AudioMuse settings schema (enabled, base URL, credential)](tickets/08-audiomuse-settings-schema.md):
  add `audiomuse_enabled` (bool, false, "Enable AudioMuse-AI integration"),
  `audiomuse_base_url` (string, "", "AudioMuse-AI base URL"), and secret
  `audiomuse_api_key` (string, "", sent as Bearer when non-empty — the real
  API uses an optional API token; `type: "secret"` is Fernet-encrypted at
  rest on live fnack core).
- [Decide similarity sourcing + translation + fallback for getSimilarSongs/getSimilarSongs2](tickets/09-similarity-sourcing-fallback.md):
  call `GET {base}/api/similar_tracks?item_id=<tr-id>&n=<count>` via
  context.http with Bearer when keyed; item_id = fnack Subsonic id with
  title+artist fallback (user decision); normalize → Subsonic song list;
  AudioMuse-first/fnack-fallback with smallest-valid response when
  disabled/unavailable; both endpoints share one provider path.
- [Decide getArtistInfo/getArtistInfo2 integration scope](tickets/10-artist-info-integration.md):
  AudioMuse has no artist-info endpoint → similarity-only; no invented
  endpoint; getArtistInfo/2 return minimal valid response with fnack-side data
  only; document integration applies to similarity.
- [Decide whether to add a "Test AudioMuse-AI connection" plugin action](tickets/11-connection-test-action.md):
  add the optional action — live fnack core v0.3.21 supports manifest
  `actions` (`POST /api/plugins/<id>/action/<action_id>` → snake_cased method,
  settings-modal button), so the connection test fits conventions; fails soft
  when disabled/unreachable.
- [Decide the implementation home + versioning + release workflow](tickets/12-implementation-home-versioning.md):
  canonical edit target fnack-plugins `plugins/fnack.subsonic/` → package +
  parity → PR → vendor into fnack bundled_plugins → tag core release; keep
  `api_version ^1.0`, bump plugin version per repo convention, raise
  `min_core_version` to the v0.3.21-era release (enforced permissions +
  capabilities/actions + secret-at-rest) that the upgraded plugin depends on.
- [Decide the OpenSubsonic conformance level](tickets/13-opensubsonic-conformance-level.md):
  Standard OS v1 (user decision): classic contract + OS envelope attrs
  (`type`/`serverVersion`/`openSubsonic: true`), error codes 41–44, `apiKey`
  auth, `getOpenSubsonicExtensions`; defer formPost + extended OS-only fields.
- [Decide the enabled-by-default + route-gating semantics of the Subsonic plugin](tickets/14-enabled-gating-semantics.md):
  gate on `enabled`, default flips to `true` (user decision); fnack core only
  registers /rest routes for manager-enabled plugins at boot, and the plugin's
  own `enabled` setting (previously cosmetic) should gate serving too — flip
  default to true and migrate old cosmetic-false installs; AudioMuse stays
  independent via `audiomuse_enabled`.
- [Decide the automated-test + verification scope](tickets/15-test-verification-scope.md):
  plain-python plugin tests (no pytest/network) in fnack-plugins conventions +
  XML/JSON fixtures from ticket 03 + mocked context.http per ticket 02;
  disabled/ failure/ settings/ permissions/ architecture guards; documented
  live curl + client smoke procedure; report live vs mock vs unit honestly.
- [Add a narrow core API capability for local cover art](tickets/16-cover-art-core-capability.md):
  add a small plugin-facing core API addition to expose local cover-art
  lookup (user decision), so getCoverArt serves real bytes instead of error 70
  or proxying URLs; details deferred to the fnack core implementation session.

## Out of scope

- Any code change to `tajanthind/fnack` or `tajanthind/fnack-plugins` from
  this tracker (user constraint; execution happens in a later session against
  those repos, in their own branch/PR workflow).
- Bundling, installing, or running AudioMuse-AI inside fnack; a second
  AudioMuse plugin; a second `/rest` implementation.
- Rewriting fnack core services, downloaders, or the plugin framework itself
  beyond the minimal plugin-API addition ticket 16 justifies (cover-art core
  capability).

## Map status

**Complete** — the frontier is empty. Every research ticket resolved with
findings in `research/`, and every decision ticket resolved with a recorded
answer, gisted above. A later execution session against
`tajanthind/fnack-plugins` (+ the `fnack` bundled mirror) can now run the brief
(§1–§33) as an implementation order without re-deciding anything. Tracked
deliberately from `navmuse`; fnack and fnack-plugins were treated as read-only
ground truth throughout.

> Addendum (2026-09-04): after the map was marked complete, the up-to-date
> `docs/plugins/AUTHORING.md` was pulled from live fnack `main` (pinned at
> `reference/AUTHORING.md`) and the architecture audit was re-verified against
> live fnack `main` v0.3.21 (the first audit had used a stale local clone at
> v0.3.1). Research file 01 and tickets 01/04/06/11/12/14/15 were corrected:
> permissions are enforced fail-closed on live core, `capabilities` +
> `actions` manifest support and the `fnack.plugin_api` SDK exist, secrets are
> Fernet-encrypted at rest, and the M2M API key is auto-created at startup.
> Re-verify against live `main` before executing — the local checkouts lag the
> GitHub repos.
