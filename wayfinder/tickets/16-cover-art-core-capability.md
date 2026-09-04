# Add a narrow core API capability for local cover art

Type: grilling
Status: resolved
Blocked by: 01

## Question

`getCoverArt` currently always returns error 70 ("Cover not found (not yet
indexed)") because fnack's library facade exposes only `cover_url` (a URL) on
album dicts — no local cover-art paths/bytes. Real Subsonic clients (Symfonium,
DSub, Sublime Music) depend on `coverArt` IDs and `getCoverArt` working.

The brief §3/§10 rule: if the Subsonic API needs a library operation the
current facade does not provide, first check existing facade methods; only add
a narrowly scoped new plugin-facing capability if truly necessary — never reach
around the PluginContext boundary into models/db/app.

Decision: how should real cover art be delivered in v1?

## Resolution

RESOLVED by user decision: add a **narrowly scoped core plugin-API addition**
that exposes local cover-art lookup by entity (album/artist/track) so the
plugin can serve real bytes through `getCoverArt` — matching the brief §3
"API-gap → small core API addition" rule rather than proxying external URLs or
leaving the endpoint broken. Details to be settled in the fnack core
implementation session: exact facade method name/signature (e.g.
`library.get_cover_art(entity_kind, entity_id) -> Optional[Path/bytes]`),
where art lives on disk, and how `coverArt` IDs map (see ticket 05). The
manifest must then NOT need filesystem permissions if the facade hides the
paths; if it returns a Path the plugin may still stream via `send_file`
without extra permissions, mirroring how `stream` works today.
