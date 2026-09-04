# Decide similarity sourcing + translation + fallback for getSimilarSongs/getSimilarSongs2

Type: grilling
Status: resolved
Blocked by: 02, 03

## Question

How should `getSimilarSongs` and `getSimilarSongs2` obtain their results, and
what is the fallback when AudioMuse is disabled or unavailable (brief §15,
§16, §17, §19, §20, §23)?

The brief dictates the policy — AudioMuse-first, fnack-fallback — and the
architecture: when enabled and reachable, use the real AudioMuse API contract
(ticket 02) for sonic-similarity; when disabled/unavailable/malformed, fall
back to fnack's existing behavior, or if no local similarity implementation
exists, return the smallest valid Subsonic response rather than a server error.
Do not expose AudioMuse's response format directly: a translation layer
(AudioMuse response → normalized similarity representation → Subsonic
response) keeps AudioMuse field names isolated from the route layer. All
AudioMuse calls via `context.http` with explicit timeouts; failures handled
locally; no secret values logged.

The genuinely open bits to settle once ticket 02 lands: the exact mapping from
Subsonic `id` (song) to AudioMuse's track identifier, the normalized
representation's minimum fields, and whether getSimilarSongs2's semantics
differ from getSimilarSongs1 in this implementation (spec research, ticket 03:
with ID3 organization either endpoint may be used and results match for artist
ids — so both can share the same provider path).

## Resolution

RESOLVED from AudioMuse research (ticket 02) + spec (ticket 03) + brief
§15/§16/§17/§19/§20/§23 + user decision (id alignment):

- **Provider call**: `GET {base_url}/api/similar_tracks?item_id=<fnack Subsonic
  track id>&n=<count>` via `context.http`, adding `Authorization: Bearer
  <audiomuse_api_key>` only when a key is set. Optional `server` param omitted
  unless the deployment needs it. Explicit timeout (~5–10s); no long-running
  background requests. (Endpoints confirmed by the Go Navidrome plugin and the
  Open Subsonic MusicServer mapping.)
- **ID alignment (user decision)**: when AudioMuse indexes fnack through a
  provider consuming fnack's own Subsonic/OpenSubsonic endpoint, its item_ids
  ARE fnack's Subsonic track ids (`tr-<id>`) and round-trip cleanly. When an
  item_id lookup misses, fall back to `title`+`artist` reference on AudioMuse's
  side. The exact provider/deployment alignment is flagged for live validation
  (research file `02`).
- **Translation layer** (brief §19): AudioMuse rows
  (`item_id,title,author,album,distance,…`) → internal normalized similarity
  representation (minimum: resolved fnack track id + title/artist/album) →
  Subsonic `<similarSongs>/<similarSongs2><song Child>` list. AudioMuse field
  names stay isolated from route handlers.
- **Fallback policy (AudioMuse-first, fnack-fallback)**: disabled /
  unreachable / timeout / 4xx / 5xx / invalid JSON / missing fields / empty /
  unknown track → return the smallest valid Subsonic response (empty
  `similarSongs`/`similarSongs2` child list), never a server error. fnack has
  no local similarity implementation today, so there is nothing to preserve —
  document that (brief §17.5, §23).
- Both `getSimilarSongs` and `getSimilarSongs2` share one provider path
  (spec: results match for artist ids under ID3 organization; count default 50
  → map to `n`).
