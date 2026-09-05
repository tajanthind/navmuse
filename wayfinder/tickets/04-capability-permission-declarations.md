# Decide capability + permission declarations for the upgraded Subsonic plugin

Type: grilling
Status: resolved
Blocked by: 01

## Question

Which manifest `capabilities` and `permissions` should the upgraded
`fnack.subsonic` plugin declare (brief §4, §5, §22)?

The brief is explicit that we must not invent capability IDs, must use existing
capability constants where appropriate, and must not force the feature into an
inappropriate capability — a pure `server_extension` implementation is
acceptable when that is the architecture's intended model. Permission-wise it
declares only what is actually used: `settings` (plugin settings), `network`
(AudioMuse outbound HTTP via `context.http`), and filesystem permissions only
where the current `context.fs` semantics actually require them.

Resolution depends on ticket 01's audit of the real capability registry and
permission model (which constants exist today, how undeclared access is
enforced, how the existing plugin.json is validated).

## Resolution

RESOLVED from the corrected live audit (ticket 01) + brief §4/§5/§22:

- **Capabilities**: on live fnack main v0.3.21 the capability model the brief
  describes is REAL: manifest `capabilities` field exists, `fnack/plugin_api/
  capabilities.py` exports `SERVER_EXTENSION = "server.extension"` (and other
  constants), the manager derives capabilities from `type` when omitted
  (server_extension → server.extension), unknown IDs warn forward-compatibly,
  and contracts.py validates that declared capabilities are implemented
  (missing → skipped with warning, not a load failure). Decision: the upgraded
  plugin keeps `capabilities: ["server.extension"]` — the existing canonical
  manifest value, now backed by a real constant; do NOT invent new capability
  IDs (there is no similarity/recommendation capability constant; a pure
  server_extension stays the architecture's model for this feature).
- **Permissions**: live core enforces them fail-closed. The upgraded plugin
  must declare exactly what it uses: `settings` (settings_schema +
  context.settings for the AudioMuse toggles/key), `library:read` (every
  library read incl. get_api_key/list_*/get_*), `network` (context.http for
  AudioMuse — **mandatory**: without it context.http is None and any AudioMuse
  call would AttributeError), and `filesystem:music` ONLY if streaming moves
  behind `context.fs.open_music_path`. Today the plugin streams raw via
  send_file on `local_path`, so filesystem:music is currently
  declared-but-unused (a warning on live core) — drop it or actually use the
  fs facade. `library:write` is NOT needed (no get_or_create_api_key call
  planned in the plugin — read-only auth).
