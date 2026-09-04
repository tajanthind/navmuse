# Brief: Subsonic-API compatibility + optional AudioMuse-AI integration for fnack

This brief is self-contained. Execute it against the **current `main` branch of
`tajanthind/fnack`**. Do not rely on older fnack plugin documentation,
previous versions of the plugin architecture, or assumptions from this brief
when the repository itself provides a newer implementation.

The repository is the source of truth for all fnack-specific APIs.

---

# 1. Objective

Bring fnack's existing Subsonic server-extension plugin to a solid,
real-world **Subsonic/OpenSubsonic-compatible REST implementation**, while
adding an **optional AudioMuse-AI integration** inside that same plugin.

The finished feature must allow:

1. normal Subsonic-compatible clients to browse, search, stream, and download
   fnack's music library through `/rest/*`;
2. fnack to remain fully functional when AudioMuse-AI is not installed,
   configured, or reachable;
3. users to optionally configure an external AudioMuse-AI instance through
   the normal fnack plugin settings UI;
4. AudioMuse-AI sonic similarity to supply Subsonic
   `getSimilarSongs` / `getSimilarSongs2` results when enabled and available;
5. the implementation to conform to the **current fnack plugin API and
   capability architecture**.

Do not create a second plugin for AudioMuse-AI. The Subsonic API and the
optional sonic-similarity integration are one coherent feature.

---

# 2. IMPORTANT: inspect the current fnack architecture first

Before writing code, inspect the current repository and establish the exact
APIs currently implemented.

At minimum inspect:

```text
plugins/base.py
plugins/context.py
plugins/__init__.py
docs/plugins/AUTHORING.md
docs/plugins/
fnack/plugin_api/
```

Also inspect the plugin manager, capability registry, permission enforcement,
plugin manifest validation, and the existing Subsonic plugin wherever it is
actually located in the current tree.

Do not assume paths.

Do not assume that the existing Subsonic implementation lives at:

```text
plugins/subsonic/
```

Find the real current location first.

Likewise, locate the current Subsonic manifest rather than assuming its name,
schema, or directory layout.

---

# 3. Current fnack plugin architecture requirements

The implementation MUST target the current plugin architecture found in
`main`.

The current architecture defines:

```python
class PluginBase(ABC)
```

with typed plugin interfaces including:

```python
ServerExtensionPlugin
RecommendationPlugin
MetadataProviderPlugin
DownloaderPlugin
FingerprintPlugin
ScanTriggerPlugin
LibraryTaskPlugin
VPNPlugin
UIExtensionPlugin
EventHookPlugin
LyricsProviderPlugin
StorageBackendPlugin
AuthProviderPlugin
LibrarySourcePlugin
ConflictResolverPlugin
```

For this feature, the primary interface is:

```python
ServerExtensionPlugin
```

which requires:

```python
def register_routes(self, blueprint) -> None:
    ...
```

The plugin receives a `PluginContext` and must interact with fnack through
that context rather than directly using fnack internals.

The current architecture explicitly treats `PluginContext` as the compatibility
boundary. Plugins must NOT directly import or use:

```text
models
db/session
Flask app
core internal services
```

unless the current repository has explicitly exposed that capability through the
plugin API.

The current `PluginContext` exposes narrow facades including:

```text
context.library
context.settings
context.events
context.http
context.fs
context.ui
context.jobs
context.log
```

Use those current facades exactly as implemented in the repository.

Do not invent helper methods.

Do not bypass the context boundary merely because an internal fnack function
would be easier to call.

If a capability required by the implementation is missing from the current
plugin API, treat that as an API-gap that must be solved through an appropriate
small core API addition rather than reaching around the boundary.

The current authoring guide explicitly states that plugins have no direct
database/app access and that missing capabilities should be exposed through
the plugin API rather than through imports of `models` or `services.*`.


---

# 4. Current manifest architecture

Use the current `plugin.json` manifest format.

The current API contract includes fields such as:

```json
{
  "id": "...",
  "name": "...",
  "version": "...",
  "type": ["server_extension"],
  "api_version": "^1.0",
  "entry_point": "plugin:PluginClass",
  "min_core_version": "...",
  "permissions": [],
  "settings_schema": [],
  "ui": {},
  "actions": [],
  "dependencies": {},
  "trust_level": "...",
  "capabilities": []
}
```

Do not downgrade the plugin to an older manifest format.

The current plugin API uses:

```text
api_version: "^1.0"
```

for plugins targeting fnack plugin API 1.x.

The manifest also supports explicit capability IDs. The current implementation
allows a plugin to advertise one or more capabilities, with unknown IDs being
forward-compatible warnings rather than hard failures. Inspect the current
capability definitions and registry before deciding whether this feature
requires an explicit capability declaration.

Do not invent capability IDs.

Use existing capability constants where appropriate.

If no appropriate capability currently exists, document whether the feature
should remain a pure `server_extension` route contribution or whether a
small new capability is warranted.

---

# 5. Permission model

Use the current fnack permission model.

Relevant current permissions include, where actually required:

```text
network
settings
filesystem:downloads
filesystem:music
```

Only declare permissions actually used.

The current `PluginContext` documentation specifies:

```text
context.settings -> settings
context.http     -> network
context.fs       -> filesystem permissions where applicable
```

and permission enforcement rejects undeclared capability access. Declared but
unused permissions are also surfaced as warnings.

For AudioMuse-AI:

- outbound HTTP must use the current `context.http`;
- plugin settings must use `context.settings`;
- do not use direct `requests` / `urllib` / socket calls from the plugin if
  the current context HTTP facade is available.

The current `context.http` is a preconfigured `requests.Session` intended for
plugin outbound HTTP and governed by the `network` permission.

---

# 6. Plugin lifecycle

Respect the current plugin lifecycle:

```python
on_load()
on_enable()
on_disable()
on_unload()
on_settings_changed(settings)
```

Do not perform AudioMuse network access during import or module initialization.

Do not make AudioMuse-AI connectivity a startup requirement.

If any client/cache/session state is created, clean it up appropriately in the
corresponding lifecycle method.

Remember that current fnack v1 loads plugins in-process and wraps plugin calls
with timeout/exception handling. Repeated failures can automatically disable
a plugin. Therefore the AudioMuse integration MUST fail softly and avoid
turning an unavailable external service into repeated plugin failures.


---

# 7. Existing Subsonic implementation audit

Before modifying anything, locate the current bundled/installed Subsonic
plugin and create an implementation inventory.

Determine exactly which of the following are already implemented:

```text
ping.view
authentication
getMusicFolders
getIndexes
getArtists
getArtist
getAlbum
getMusicDirectory
getCoverArt
stream
download
search3
getSimilarSongs
getSimilarSongs2
getArtistInfo
getArtistInfo2
```

Also inspect:

```text
XML response structure
JSON response structure
response envelopes
status/error handling
content types
charset handling
parameter parsing
media ID mapping
artist/album/track ID mapping
cover-art IDs
streaming/range behavior
download behavior
missing-file behavior
authentication semantics
client compatibility quirks
tests
```

Do not duplicate an existing route.

Do not create a second `/rest` implementation.

Extend the existing Subsonic implementation wherever practical.

If the current Subsonic implementation already has a local fallback path for
similarity or artist info, preserve it and integrate AudioMuse around it.

---

# 8. Subsonic specification verification

Read the current official Subsonic API specification:

```text
https://www.subsonic.org/pages/api.jsp
```

and current OpenSubsonic documentation:

```text
https://opensubsonic.netlify.app/
```

Verify every wire-level behavior that matters to client compatibility rather
than guessing.

In particular verify:

```text
parameter names
required parameters
optional parameters
response object names
XML nesting
JSON nesting
response status/version attributes
error codes
ID handling
stream/download semantics
search3 request/response structure
getSimilarSongs request/response structure
getSimilarSongs2 request/response structure
getArtistInfo/getArtistInfo2 structure
```

Use the actual specification as the contract.

---

# 9. Subsonic authentication

Inspect fnack's CURRENT authentication architecture before implementing or
changing Subsonic authentication.

Fnack remains zero-required-auth by default.

Do not introduce a mandatory login requirement for the entire fnack
application.

However, the `/rest/*` implementation must correctly handle the authentication
mechanism required by Subsonic clients when credentials are supplied.

Determine from the current fnack implementation how the plugin should
integrate with:

```text
u
p
t
s
v
c
api-key style authentication
```

and any current fnack API-key behavior.

The current `PluginContext.library` exposes:

```python
get_api_key()
get_or_create_api_key()
```

for server-extension/integration use, specifically to avoid plugins reaching
directly into the database. Inspect and use those APIs only where they match
the repository's current authentication contract.

Do not create a parallel authentication database or auth subsystem inside the
plugin unless the current architecture explicitly requires it.

---

# 10. Library access

Use the current library facade.

The current plugin context exposes read-oriented methods including:

```python
context.library.get_track(track_id)
context.library.get_album(album_id)
context.library.get_artist(artist_id)

context.library.list_artists()
context.library.list_albums(artist_id=None, limit=...)
context.library.list_tracks(album_id=None, limit=...)
```

These methods return plain dictionaries rather than ORM instances.

Use those APIs for Subsonic data generation.

Do not import:

```text
models
db
Track
Album
Artist
```

from plugin code.

Likewise, do not access SQLAlchemy sessions directly.

If the Subsonic API needs a library operation that the current facade does not
provide, first determine whether another existing facade method already covers
it.

Only add a narrowly scoped new plugin-facing capability if truly necessary.

---

# 11. Subsonic ID strategy

Inspect the existing plugin's current ID mapping.

Do not blindly expose internal database IDs without understanding the existing
contract.

If current fnack behavior already uses stable numeric IDs, preserve it unless
the actual Subsonic compatibility testing demonstrates a problem.

If the plugin requires a translation layer, implement it consistently across:

```text
artist
album
track
cover art
stream
download
similar songs
artist info
```

Do not change the existing ID contract gratuitously.

---

# 12. Required AudioMuse-AI integration

AudioMuse-AI is an external, separately deployed application.

Fnack MUST NOT:

```text
bundle AudioMuse-AI
install AudioMuse-AI
run AudioMuse-AI
start another container
run Librosa/ONNX analysis itself
require AudioMuse-AI for startup
require AudioMuse-AI for normal Subsonic browsing
```

Fnack only optionally communicates with an already-running external
AudioMuse-AI instance.

---

# 13. AudioMuse repository inspection

Before writing the integration, inspect the CURRENT AudioMuse-AI repository:

```text
https://github.com/NeptuneHub/AudioMuse-AI
```

Specifically inspect:

```text
docs/ARCHITECTURE
docs/PLUGINS
docs/CONFIGURATION PARAMETERS
API/router implementation
Docker configuration
examples
configuration files
authentication implementation
```

Do not assume the API shape.

Determine from the actual source/docs:

```text
default port
base URL conventions
API prefix
similarity endpoint
artist-info endpoint, if any
HTTP methods
query parameters
JSON request fields
JSON response fields
authentication requirements
timeouts/rate limits, if documented
track/artist identifier format
error responses
```

If the documentation differs from the actual implementation, treat the
running source as authoritative and record the discrepancy.

Do not fabricate an artist-info endpoint if AudioMuse does not provide one.

---

# 14. AudioMuse settings

Add AudioMuse-AI settings to the EXISTING Subsonic plugin's
`settings_schema`.

Use normal fnack plugin settings; do not create a custom settings system.

Required settings:

### `audiomuse_enabled`

```text
type: boolean
default: false
required: false
```

Display label:

```text
Enable AudioMuse-AI integration
```

### `audiomuse_base_url`

```text
type: string
default: ""
required: false
```

Display label:

```text
AudioMuse-AI base URL
```

Do not hardcode a default URL unless verified from the actual current
AudioMuse-AI repository.

### AudioMuse credential

Only add this when the actual AudioMuse implementation requires one.

Use:

```text
type: secret
default: ""
required: false
```

and select a clear key such as:

```text
audiomuse_api_key
```

only if the actual AudioMuse API uses an API key/token.

Do not invent credentials that AudioMuse does not use.

---

# 15. AudioMuse HTTP implementation

When enabled, use:

```python
self.context.http
```

for communication with AudioMuse-AI.

Do not use direct external networking when the context HTTP facade is
available.

Declare:

```text
network
```

in the plugin manifest only because AudioMuse communication actually requires
it.

All AudioMuse calls should have explicit reasonable timeouts.

Do not create long-running background requests.

Do not block unrelated fnack functionality waiting indefinitely for AudioMuse.

---

# 16. AudioMuse disabled behavior

The default state MUST be:

```text
audiomuse_enabled = false
```

When disabled:

```text
no AudioMuse HTTP request
no DNS/connection attempt
no AudioMuse initialization
no AudioMuse dependency
no behavioral change to normal fnack operation
```

The rest of the Subsonic API must work exactly as before.

This is a strict compatibility requirement.

---

# 17. Similar-song integration

When:

```text
audiomuse_enabled = true
```

and the AudioMuse service is correctly configured and reachable:

```text
getSimilarSongs
getSimilarSongs2
```

must obtain sonic-similarity results from AudioMuse-AI.

Use the actual AudioMuse API contract discovered during repository inspection.

For this feature use the following policy:

> AudioMuse-first, fnack-fallback.

That means:

1. AudioMuse-AI returns valid similarity data:
   use that data for the Subsonic response.

2. AudioMuse-AI is unavailable:
   use fnack's existing fallback behavior, if any.

3. AudioMuse-AI returns an invalid/malformed response:
   use fnack's existing fallback behavior, if any.

4. AudioMuse integration is disabled:
   use fnack's existing behavior.

5. No local similarity implementation exists:
   return the smallest valid Subsonic response permitted by the current
   implementation rather than returning a server error merely because
   AudioMuse is absent.

Document this policy in the implementation.

---

# 18. Artist-information integration

Inspect AudioMuse's actual API before doing anything here.

If AudioMuse provides an appropriate artist-analysis/artist-information API,
integrate it into:

```text
getArtistInfo
getArtistInfo2
```

using the same:

```text
AudioMuse-first, fnack-fallback
```

semantics.

If AudioMuse does not provide equivalent functionality:

- do not invent an endpoint;
- preserve fnack's normal artist-info behavior;
- document that AudioMuse integration only applies to similarity.

---

# 19. AudioMuse response translation

Do not expose AudioMuse's response format directly to Subsonic clients.

Create a clear translation layer:

```text
AudioMuse response
        ↓
internal normalized similarity representation
        ↓
Subsonic response
```

The normalized representation should use the minimum fields required to
construct the correct Subsonic response.

Keep AudioMuse-specific field names isolated from the Subsonic route layer.

Do not spread AudioMuse-specific JSON parsing throughout the route handlers.

---

# 20. Error handling

AudioMuse failures must be isolated from normal Subsonic behavior.

Handle at minimum:

```text
connection refused
DNS failure
timeout
HTTP 4xx
HTTP 5xx
invalid JSON
missing expected fields
empty response
unknown track
unknown artist
authentication failure
```

Do not let those failures escape as unhandled plugin exceptions.

Do not log credentials.

Do not log Authorization headers.

Do not include secret values in error messages.

Do not cause the plugin to become repeatedly unhealthy merely because the
optional external service is offline.

The current plugin manager has automatic exception guarding and can auto-disable
a plugin after repeated failures, so external-service errors must be handled
locally and converted into normal fallback behavior.

---

# 21. Plugin actions

Inspect whether the current plugin architecture supports an appropriate
connection-test action through the manifest's current `actions` mechanism.

If useful and consistent with the existing Subsonic plugin UX, add an optional
action such as:

```text
Test AudioMuse-AI connection
```

Only do this if it fits the existing plugin conventions.

Do not make the action required for the feature.

Do not create a second UI surface.

The current plugin manifest supports declarative `actions` that invoke methods
on the plugin instance.

---

# 22. Capabilities

Inspect the current `fnack.plugin_api.capabilities` implementation.

Determine whether:

```text
recommendation
similarity
server-extension
```

or another existing capability should be advertised.

If an existing capability is appropriate, use its exported constant rather than
a string invented in the plugin.

If no suitable capability exists, do not force this feature into an
inappropriate capability. A pure server-extension implementation is acceptable
when that is the architecture's intended model.

Do not introduce a new capability unless the current architecture clearly
requires it and the addition is justified.

---

# 23. Existing fallback behavior

Preserve whatever fallback behavior the current Subsonic plugin already has.

Do not rewrite existing recommendation logic merely to integrate AudioMuse.

The integration should be additive:

```text
existing Subsonic implementation
            +
optional AudioMuse provider
```

not:

```text
replace entire Subsonic implementation with AudioMuse-specific logic
```

---

# 24. Tests

Add or update automated tests for the existing Subsonic plugin.

At minimum cover:

### Subsonic API

```text
ping.view
getMusicFolders
getArtists
getArtist
getAlbum
getMusicDirectory
getCoverArt
stream
download
search3
```

plus any endpoints the audit identifies as already implemented.

### AudioMuse disabled

Verify:

```text
audiomuse_enabled = false
```

causes:

```text
zero AudioMuse HTTP calls
normal Subsonic behavior
no regression
```

### AudioMuse enabled

Mock AudioMuse using the exact API shape discovered from the real repository.

Verify:

```text
correct HTTP endpoint
correct HTTP method
correct parameters
correct authentication
correct result translation
correct getSimilarSongs output
correct getSimilarSongs2 output
```

### AudioMuse failure

Mock:

```text
timeout
connection failure
500
invalid JSON
malformed similarity response
```

and verify fnack falls back gracefully.

### Settings

Verify:

```text
audiomuse_enabled defaults to false
audiomuse_base_url defaults to ""
secret setting is not logged
settings are stored through context.settings
```

### Permissions

Verify:

```text
network is declared when AudioMuse HTTP is used
settings is declared when plugin settings are accessed
no unnecessary permissions are declared
```

### Architecture

Verify the plugin does NOT import:

```text
models
db
app
services.*
```

directly.

---

# 25. Live/manual verification

Add a documented smoke-test procedure.

## A. Real Subsonic verification

Against a real running fnack instance:

```text
GET /rest/ping.view
GET /rest/getMusicFolders.view
GET /rest/getArtists.view
GET /rest/getArtist.view
GET /rest/getAlbum.view
GET /rest/getMusicDirectory.view
GET /rest/search3.view
```

Then verify:

```text
GET /rest/stream.view
```

actually plays a real track.

Use at least:

```text
curl
```

plus a real Subsonic-compatible client where practical.

Verify:

```text
browse artists
browse albums
browse tracks
search
play a track
```

---

# 26. AudioMuse-off verification

Run fnack with:

```text
audiomuse_enabled = false
```

and verify:

```text
fnack starts even without AudioMuse
Subsonic browsing works
streaming works
search works
no AudioMuse network request occurs
similar-song endpoint remains valid
```

---

# 27. AudioMuse-on verification

Run a real or realistically mocked AudioMuse-AI instance whose API matches
the inspected source.

Configure:

```text
audiomuse_enabled = true
audiomuse_base_url = <actual verified URL>
```

Then verify:

```text
getSimilarSongs
getSimilarSongs2
```

return sonic results derived from AudioMuse.

Also verify artist-info integration if the real AudioMuse API supports it.

---

# 28. Unavailable AudioMuse verification

Stop AudioMuse or point the plugin at an unavailable endpoint.

Verify:

```text
Subsonic API still works
browsing still works
streaming still works
search still works
similarity falls back cleanly
fnack does not crash
plugin does not become permanently unusable
```

---

# 29. Repository workflow

Inspect the CURRENT repository workflow before committing.

Check:

```text
CONTRIBUTING.md
recent PRs
recent merged plugin changes
branch naming
test commands
lint commands
formatting commands
plugin release/versioning process
bundled plugin update process
plugin repository/index process
```

Do not assume a historical workflow.

Follow whatever the current repository establishes.

If bundled `fnack.subsonic` is part of the main image, update the appropriate
bundled-plugin source and any required registry/index metadata.

Do not push directly to `main` unless the repository explicitly uses that
workflow.

Prefer a focused branch and PR when that is the established contribution model.

---

# 30. Versioning

Update the Subsonic plugin version according to the repository's current
versioning conventions.

Do not change the plugin API major version.

Keep:

```text
api_version: "^1.0"
```

unless inspection of the current repository proves that the plugin API has
moved to a newer major version.

Use the current `min_core_version` only if required by an API introduced after
the plugin's current minimum supported fnack release.

---

# 31. Documentation

Update the plugin documentation/implementation notes to explain:

```text
existing Subsonic endpoints
newly added/fixed endpoints
AudioMuse settings
AudioMuse API endpoint(s)
authentication mechanism
request/response mapping
fallback behavior
timeouts
failure handling
ID mapping
known limitations
```

Clearly distinguish:

```text
verified from source
verified by live testing
mock-tested
inferred/uncertain
```

Never present an inferred AudioMuse API detail as confirmed fact.

---

# 32. Final report

When finished, report:

## Existing vs newly implemented

Provide a concise table:

```text
Endpoint                 Existing | Changed/Added
-------------------------------------------------
ping.view                 ...
getArtists                ...
getArtist                 ...
...
```

## Exact settings

Report:

```text
audiomuse_enabled
type: boolean
default: false

audiomuse_base_url
type: string
default: ""

<credential if applicable>
type: secret
default: ""
```

Use the actual final manifest keys.

## Architecture compliance

Explicitly confirm:

```text
current api_version used
current ServerExtensionPlugin interface used
current PluginContext used
direct ORM access: none
direct Flask app access: none
AudioMuse via context.http
settings via context.settings
permissions reviewed
capabilities reviewed
single plugin
optional integration
no second container
no startup dependency
```

## Verification status

Explicitly state:

```text
A. real Subsonic browse/stream: PASS/FAIL
B. AudioMuse disabled: PASS/FAIL
C. AudioMuse enabled: PASS/FAIL
```

Separate:

```text
live-tested
mock-tested
unit-tested
not verified
```

Do not claim live verification if it was only mocked.

## AudioMuse API findings

Report the actual:

```text
base URL / port
API prefix
endpoint
method
parameters
authentication
response fields
identifier mapping
errors/fallback behavior
```

and explicitly list any ambiguity that still needs validation against a real
AudioMuse deployment.

---

# 33. Hard constraints

Do NOT:

```text
create a second Subsonic plugin
create a second AudioMuse plugin
bundle AudioMuse-AI
run AudioMuse-AI inside fnack
add a second Docker container
directly query SQLAlchemy from plugin code
import fnack.models from plugin code
import fnack.services from plugin code
access Flask app internals
invent AudioMuse endpoints
invent AudioMuse response fields
make AudioMuse mandatory
make the AudioMuse toggle default to true
break zero-auth-by-default fnack behavior
change unrelated plugin architecture
duplicate existing Subsonic routes
```

Do:

```text
inspect current source first
use the current plugin API
use ServerExtensionPlugin
use PluginContext
use current manifest schema
use permissions correctly
use current library facade
use current settings facade
use current HTTP facade
preserve existing Subsonic behavior
integrate AudioMuse additively
fail soft when AudioMuse is unavailable
test the actual Subsonic wire format
verify AudioMuse against its actual source
document every uncertainty
```

The repository source and current plugin API are authoritative over every
assumption in this brief.