# Decide the OpenSubsonic conformance level

Type: grilling
Status: resolved
Blocked by: 01, 03

## Question

How far into OpenSubsonic should the upgraded plugin go (brief §8 says to
verify against both the classic Subsonic spec and OpenSubsonic docs; the plugin
README and manifest claim Subsonic/OpenSubsonic support for Symfonium/DSub/
Sublime Music)?

The wire-spec research (ticket 03) shows OS is layered on top of classic:
response envelope gains required `type`, `serverVersion`, `openSubsonic`
attributes; new error codes 41–44; `apiKey` auth extension; optional
`formPost` POST support; `getOpenSubsonicExtensions` endpoint; extended
Child/AlbumID3 field sets; empty-query search3 support; getCoverArt id
semantics tightened.

Decide the target conformance level:
(a) minimal OS: classic XML/JSON contract + OS envelope attributes
   (`openSubsonic: true`), no extensions endpoint, no apiKey param, no formPost;
(b) standard OS v1: (a) + `getOpenSubsonicExtensions` + error codes 41–44 +
   `apiKey` auth mapped onto fnack's API key;
(c) full OS v1: (b) + formPost + extended fields where fnack's data model can
   supply them.

Recommendation: (b) — standard OS v1. It matches "Subsonic/OpenSubsonic
compatible" claims without inventing data fnack doesn't hold ((c) adds little
for real clients and (a) underclaims after the OS envelope is trivial).

## Resolution

RESOLVED by user decision: target **Standard OS v1** — the classic XML/JSON
contract plus OpenSubsonic envelope attributes (`type`, `serverVersion`,
`openSubsonic: true` on every response), OS error codes 41–44, and the OS
`apiKey` auth param mapped onto fnack's M2M API key. Also implement
`getOpenSubsonicExtensions` (no-auth) so clients can discover what the server
supports. Defer formPost (option c) and extended OS-only Child/AlbumID3 fields
unless a client interop test shows they're needed — fnack's data model
provides the classic field set, and option (c)'s extras add little for the
target clients (Symfonium/DSub/Sublime Music). Response `version` claims
1.16.1 (classic) with the OS attributes layered on.
