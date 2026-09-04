# Subsonic + OpenSubsonic wire contract — verified findings

Ticket: 03-verify-subsonic-opensubsonic-wire-contract (research)
Status: resolved
Sources: subsonic.org/pages/api.jsp (S), subsonic-rest-api-1.16.1.xsd (S-XSD),
example XMLs under subsonic.org/pages/inc/api/examples (S-EX),
opensubsonic.netlify.app docs sourced from github.com/opensubsonic/open-subsonic-api (OS).
Note: the canonical Open Subsonic org is `opensubsonic`; `NeptuneHub/open-subsonic-api`
and `NeptuneHub/AudioMuse-AI-MusicServer` are forks.

## Base URL, methods, common params

- Base: `http://your-server/rest/<name>` — the `.view` suffix is optional/no-op.
- GET (classic); OS adds POST `application/x-www-form-urlencoded` as the `formPost`
  extension (server must signal it via `getOpenSubsonicExtensions`; unsupported → HTTP 405).
- Common params: `u` required, `p` (plain or `enc:` hex) OR `t`+`s` (since 1.13.0),
  `v` required (protocol version; OS servers should support ≥ 1.14.0, ideally 1.16.1),
  `c` required (client id), `f` optional default `xml` (`json` since 1.4.0).
  OS adds `apiKey` auth extension (query param, no `u`), and errors 41 (token auth
  unsupported), 42 (mechanism unsupported), 43 (conflicting auth), 44 (invalid API key).

## Response envelope

- XML root `<subsonic-response xmlns="http://subsonic.org/restapi" status="ok|failed"
  version="…">` with one payload child, incl. `<error code= message=/>` on failure.
- OS adds required attributes `type` (server name), `serverVersion`, `openSubsonic`
  (bool, must be true when OS v1 supported). JSON wrapper key is identical:
  `{"subsonic-response": {…}}`; XML attributes → JSON properties; repeated XML children
  → JSON arrays (single-element arrays stay arrays).
- Errors travel as HTTP 200 + `status:"failed"` (OS OpenAPI only documents 200 and 405);
  classic S never fixes the HTTP status for errors.
- Encoding UTF-8. XML content-type value not mandated; OS OpenAPI uses
  `application/json` for JSON endpoints, `application/binary` / `text/xml` for
  stream/download/getCoverArt error bodies.

## Endpoint-by-endpoint (this effort's set)

- ping: no params → empty ok response (OS adds type/serverVersion/openSubsonic attrs).
- getLicense: no params → `<license valid=… email=… licenseExpires=…/>`.
- getMusicFolders: no params → `<musicFolders><musicFolder id name/>…`.
- getIndexes: opt `musicFolderId`, `ifModifiedSince` → `<indexes lastModified ignoredArticles>`
  with `shortcut*`, `index name=… > artist*`, `child*`.
- getArtists: opt `musicFolderId` → `<artists ignoredArticles><index name><artist id name
  coverArt albumCount>` (ArtistID3; XSD also requires albumCount).
- getArtist: req `id` → `<artist>` = ArtistID3 attrs + `album*` AlbumID3.
- getAlbum: req `id` → `<album>` = AlbumID3 attrs + `song*` Child.
- getMusicDirectory: req `id` → `<directory id name parent>` + `child*`.
- getAlbumList2: req `type` (random/newest/frequent/recent/starred/alphabeticalByName/
  alphabeticalByArtist/byYear/byGenre; OS adds `highest`), opt `size` (def 10, max 500),
  `offset`, `fromYear`/`toYear` (req iff byYear), `genre` (req iff byGenre),
  `musicFolderId` → `<albumList2><album AlbumID3>`.
- getSong: req `id` → `<song>` = Child.
- getCoverArt: req `id` (classic: song/album/artist id; OS: coverArt ID only as returned
  by entities), opt `size` → binary image.
- stream: req `id`, opt `maxBitRate`, `format`, `timeOffset`, `size`, `estimateContentLength`,
  `converted` → binary; error = XML body with content-type starting `text/xml`.
  OS: server must NOT auto-count as a play.
- download: req `id` only → original bytes, no transcoding.
- search3: req `query` (OS: MUST support empty query), opt artist/album/song Count+Offset,
  musicFolderId → `<searchResult3>` with `artist*` ArtistID3, `album*` AlbumID3, `song*` Child.
- getSimilarSongs: req `id` (artist/album/song), opt `count` (def 50) → `<similarSongs><song Child>`.
- getSimilarSongs2: req `id` (artist id per S; artist/album/song per OS), opt `count` →
  `<similarSongs2><song Child>`. OS: with ID3 org either endpoint may be used and results
  match for artist ids.
- getArtistInfo: req `id`, opt `count` (def 20), `includeNotPresent` → `<artistInfo>` with
  text children biography/musicBrainzId/lastFmUrl/smallImageUrl/mediumImageUrl/largeImageUrl
  + `similarArtist*` (type Artist).
- getArtistInfo2: same params → `<artistInfo2>` with same text children + `similarArtist*`
  (type ArtistID3, with coverArt/albumCount).
- getScanStatus: no params → `<scanStatus scanning count>`.

## Required vs optional Child fields (matters for song/album/artist output)

- Child required: `id`, `isDir`, `title`. Optional-but-client-critical: parent, album,
  artist, track, year, genre, coverArt, size, contentType, suffix, duration, bitRate, path,
  albumId, artistId, type ("music"), discNumber, created. OS adds optional mediaType,
  bitDepth, samplingRate, channelCount, played, bpm, isrc, musicBrainzId, genres, etc.
- AlbumID3 required: `id`, `name`, `songCount`, `duration`, `created`; optional artist,
  artistId, coverArt, year, genre…
- ArtistID3 required: `id`, `name` (+ albumCount per XSD, not per OS schema).

## ID semantics

- IDs are `xs:string`, spec never says opaque; examples use small ints or prefixed ids
  (`ar-<id>`, `al-<id>`, `tr-`-style not canonical but seen; `mf-` in OS). coverArt values
  double as getCoverArt ids. stream/download take the media (child/song) `id` from browse/
  search results.

## Notable gaps (unverified / implementer's choice)

- XML content-type header value; classic JSON content type; HTTP Range semantics (not in
  spec; Navidrome/gonic implement it server-side — implementer's concern for real clients);
  `ifModifiedSince` unchanged-collection behavior; per-endpoint error-code tables.
