# AudioMuse-AI HTTP API — ground-truth report

Ticket: 02-research-audiomuse-http-api (research)
Status: resolved
Sources (read-only, main branch): NeptuneHub/AudioMuse-AI (Flask/Python),
NeptuneHub/AudioMuse-AI-NV-plugin (Go), NeptuneHub/AudioMuse-AI-MusicServer
(Go/gin, Open Subsonic showcase). Live-deployment ambiguities listed at end.

## Server basics

- Flask + gunicorn; default port **8000** (env FLASK_BIND_PORT; compose maps
  ${FRONTEND_PORT:-8000}:8000). Image ghcr.io/neptunehub/audiomuse-ai:latest.
- No global API prefix — routes at root (`/api/...`), plus prefixed blueprints
  `/chat` and `/external`. flasgger/Swagger initialized (default UI `/apidocs`,
  verify live). SERVICE_TYPE env: `flask` = web/API only, `worker` = queue
  workers only (no HTTP). Postgres always required. No rate limits found;
  server-side timeout gunicorn --timeout 300.
- Error shapes: plain `{"error": msg}` or structured
  `{error_code, error_class, error_message, error}`; similarity/index errors
  live in 3000-3099 (3002 empty index → HTTP 503).

## Auth

- Auth layer ON by default (AUTH_ENABLED default true). Admin credentials via
  env → DB; **M2M auth = `Authorization: Bearer <API_TOKEN>`** header
  (constant-time compare, bearer callers admin-equivalent). API_TOKEN env
  default "" — token optional when blank; clients send the header only when a
  token is configured. Invalid token → 401 (per plugin READMEs). Browser auth
  uses JWT cookie via POST /auth. Exempt: /static/*, GET /api/health, /login,
  /auth, /logout (+ setup paths during first-run).

## Similarity endpoints (song → similar songs) — CONFIRMED

- **`GET /api/similar_tracks`** (primary): query params `item_id` (media-server
  track id) OR `title`+`artist` OR mood/centroid OR anchor; `n` (default 50);
  `eliminate_duplicates`, `radius_similarity`, `mood_similarity` ('true'/
  'false'); optional `server`. Response 200 = JSON array of
  `{item_id, title, author, album, distance, mood_vector, other_features,
  top_genre, top_mood, album_artist}`. Errors: 400 bad params/unknown server,
  404 track not found / "Target track not found in index or no similar tracks
  found.", 503 index empty/unavailable, 500.
- **Identifier format = the media server's own track id** (Navidrome/Subsonic/
  Jellyfin item id), NOT a path/hash. External callers send THEIR server's id;
  responses are rewritten to the requesting server's provider ids. Fallback
  reference by `title`+`artist` strings.
- Secondary: GET /api/search_tracks (autocomplete), GET /external/get_score?id,
  GET /external/get_embedding?id, GET /external/search, POST /api/hyperbolic/
  similar, POST /api/sem_grove/search, GET /api/find_path.

## Artist endpoints — similarity YES, artist-info/metadata NO

- `GET /api/similar_artists?artist=<name or artist_id>&n=&include_component_matches=`
  → array of {artist, artist_id, divergence, component_matches?}. Quirk: Go
  Navidrome plugin passes the media-server artist ID in the `artist` param;
  server resolves name-or-id — verify live.
- `GET /api/artist_tracks?artist=|artist_id=` → array {item_id, title, author}.
- `GET /api/search_artists?query=` → array {artist, track_count}.
- **No artist-biography/metadata endpoint exists** (no bios, images, last.fm
  style info, discography pages). Nothing to invent; do not fabricate one.

## How Go projects call AudioMuse (authoritative usage)

- Navidrome plugin: GET {apiUrl}/api/similar_tracks?item_id=<nd id>&n=<count>
  &eliminate_duplicates&radius_similarity[&server=]; Bearer token when set;
  apiUrl default is a hardcoded dev IP (must be configured).
- MusicServer (Open Subsonic): maps /rest/getSimilarSongs?id=<songId>&count= →
  AudioMuse GET /api/similar_tracks?item_id=<songId>&n=<count>, then resolves
  returned item_ids in its own DB — assumes shared library import so AudioMuse
  item ids == local song ids. Token via env AUDIO_MUSE_AI_TOKEN (optional);
  401 → auth failure (Subsonic error 0/503 in UI).
- Doc/code discrepancy noted in code: real path is /api/search_tracks, not an
  older /api/voyager/... prefix.

## Ambiguities resolvable only against a live deployment

1. Swagger UI path (/apidocs reachable?).
2. Exact 401/403 status + body for missing/invalid bearer on /api/*.
3. artist-vs-artist_id tolerance on /api/similar_artists across servers.
4. title+artist lookup strictness (exact vs normalized).
5. Effective config defaults per release (SIMILARITY_DEFAULT_N_RESULTS etc.).
6. Whether /api/plugins/* endpoints require auth in practice.
