# Decide getArtistInfo/getArtistInfo2 integration scope

Type: grilling
Status: resolved
Blocked by: 02

## Question

Should `getArtistInfo`/`getArtistInfo2` integrate AudioMuse (brief §18)?

The brief says: inspect AudioMuse's actual API first; if it provides an
appropriate artist-analysis/artist-information API, integrate it with the same
AudioMuse-first/fnack-fallback semantics; if it does not, do not invent an
endpoint, preserve fnack's normal artist-info behavior, and document that the
AudioMuse integration only applies to similarity.

Resolution depends on ticket 02's ground truth (does AudioMuse expose an
artist-info/artist-analysis endpoint at all?). If it does not, this ticket
resolves to "similarity-only; artist info stays whatever fnack provides."

## Resolution

RESOLVED from AudioMuse research (ticket 02) + brief §18:

AudioMuse-AI exposes **artist similarity only** (`/api/similar_artists`,
`/api/artist_tracks`) — there is **no artist-biography/metadata endpoint**.
Therefore:

- Do NOT invent an artist-info endpoint and do NOT wire AudioMuse into
  `getArtistInfo`/`getArtistInfo2`.
- `getArtistInfo`/`getArtistInfo2` (and their `.view` aliases) should return a
  minimal valid response (empty optional text children + optionally a
  `similarArtist` list sourced from fnack-side data if any exists) so clients
  don't error — per spec structure from ticket 03 — with the AudioMuse
  integration documented as **similarity-only**.
- Preserve whatever fnack-side artist-info behavior exists (none today) and
  record "AudioMuse integration only applies to similarity" in plugin docs.
