# Research the real AudioMuse-AI HTTP API

Type: research
Status: resolved
Blocked by: (none)

## Question

Before writing the integration, inspect the CURRENT AudioMuse-AI repository
(https://github.com/NeptuneHub/AudioMuse-AI) and its real consumers (brief §13,
§18): default port, base URL conventions, API prefix, similarity endpoint,
artist-info endpoint if any, HTTP methods, query parameters, JSON request
fields, JSON response fields, authentication requirements, timeouts/rate
limits, track/artist identifier format, error responses. If documentation
differs from the running source, treat the source as authoritative and record
the discrepancy. Do not fabricate an artist-info endpoint if AudioMuse does not
provide one.

## Resolution

RESOLVED (research) — findings written to
`research/02-audiomuse-http-api.md`. Highlights:

- Flask server on port 8000; no global prefix (routes at root); primary
  similarity endpoint is `GET /api/similar_tracks` (item_id OR title+artist,
  n default 50) returning a JSON array of `{item_id, title, author, album,
  distance, …}`. Track identifiers are the media server's own item ids.
- Auth: M2M via `Authorization: Bearer <API_TOKEN>` header; token optional
  (send only when configured); API server is on by default. No rate limits.
- Artist similarity exists (`GET /api/similar_artists`, `GET /api/artist_tracks`),
  but **no artist-biography/info endpoint exists** — do not invent one.
- Error style: `{error}` or structured `{error_code, error_class, …}`; empty
  index → 503. MusicServer (Go) maps `/rest/getSimilarSongs` → `/api/
  similar_tracks?item_id=<songId>` with shared item-id space.
