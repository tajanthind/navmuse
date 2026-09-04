# Decide the Subsonic ID strategy for the upgraded plugin

Type: grilling
Status: resolved
Blocked by: 01

## Question

What ID mapping should the upgraded Subsonic plugin use across artist, album,
track, cover-art, stream, download, similar-songs, and artist-info (brief §11)?

The current plugin (see audit, ticket 01) uses prefixed numeric IDs
(`ar-<artist_id>`, `al-<album_id>`, `tr-<track_id>`) and returns internal DB
ids. The brief says: do not blindly expose internal database IDs; inspect the
existing ID mapping; if current behavior already uses stable numeric IDs,
preserve it unless actual Subsonic compatibility testing demonstrates a
problem; if a translation layer is required, implement it consistently across
every surface; do not change the existing ID contract gratuitously.

The wire spec (ticket 03) says IDs are `xs:string` — nothing forces opacity,
but coverArt values double as getCoverArt IDs and must be stable across every
response that references the same entity.

## Resolution

RESOLVED from audit (ticket 01) + spec (ticket 03) + brief §11:

- **Preserve the existing prefixed-numeric contract** (`ar-<id>` artists,
  `al-<id>` albums, `tr-<id>` tracks) — it is stable, already echoed by the
  live plugin, and matches the spec (ids are `xs:string`; no opacity
  requirement; coverArt/stream/download take the same ids clients got from
  browse/search).
- Apply the SAME scheme consistently to every new surface: cover art (album
  responses emit `coverArt` = the entity's own `al-<id>`/`ar-<id>`/`tr-<id>`
  so `getCoverArt` round-trips), search results, similar-song songs, and
  artist-info similar artists. No translation layer needed as long as core
  numeric ids are stable.
- Keep `stream`/`download` taking the media (child/song) id from browse/
  search, per spec.
- Robustness fix to record: non-numeric ids after prefix-strip currently raise
  an uncaught ValueError → 500; the upgraded implementation must return
  Subsonic error 70 instead.
