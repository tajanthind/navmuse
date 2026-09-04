# Verify the Subsonic/OpenSubsonic wire contract for the endpoint set

Type: research
Status: resolved
Blocked by: (none)

## Question

Read the current official Subsonic API specification
(https://www.subsonic.org/pages/api.jsp) and the current OpenSubsonic
documentation (https://opensubsonic.netlify.app/) and verify every wire-level
behavior that matters to client compatibility rather than guessing (brief §8).
In particular: parameter names, required/optional parameters, response object
names, XML nesting, JSON nesting, response status/version attributes, error
codes, ID handling, stream/download semantics, search3 structure,
getSimilarSongs/getSimilarSongs2 structure, getArtistInfo/getArtistInfo2
structure — for the endpoint set ping, getLicense, getMusicFolders, getIndexes,
getArtists, getArtist, getAlbum, getMusicDirectory, getAlbumList2, getSong,
getCoverArt, stream, download, search3, getSimilarSongs, getSimilarSongs2,
getArtistInfo, getArtistInfo2, getScanStatus.

## Resolution

RESOLVED (research) — findings written to
`research/03-subsonic-wire-contract.md`. Highlights that shape this effort:

- Base `http://server/rest/<name>` (`.view` is optional); GET classic, POST form
  via OS `formPost` extension. Params `u`, `p`|`t+s`, `v` (server should support
  ≥1.14.0, ideally 1.16.1), `c` required; `f` default xml (`json` since 1.4.0);
  OS adds `apiKey` + errors 41–44.
- Envelope: XML root + `{"subsonic-response": …}` JSON wrapper; OS requires
  `type`, `serverVersion`, `openSubsonic` attrs. Errors travel as HTTP 200 +
  `status:"failed"` + `<error code message>`.
- XML and JSON are both first-class; a compliant server cannot be JSON-only if
  it claims classic compatibility (default format is XML). Decision recorded on
  ticket 08: implement both.
- Child required fields are minimal (`id`, `isDir`, `title`) but clients depend
  on the fuller optional set (album/artist/track/year/duration/coverArt/
  contentType/suffix/path/albumId/artistId/type…). AlbumID3 requires
  `songCount`, `duration`, `created`.
- getSimilarSongs/2 both return `<song Child>` lists keyed by `id` (artist/album/
  song depending on endpoint+OS); count default 50. getArtistInfo/2: biography +
  similarArtist (Artist vs ArtistID3).
- HTTP Range for stream is NOT in the spec (Navidrome/gonic add it server-side) —
  an implementer's concern for real-world streaming, not a conformance matter.
- This ticket resolves: a JSON-only server cannot claim classic compatibility
  (default `f` is xml); the upgraded plugin must emit both formats (see ticket 07).
