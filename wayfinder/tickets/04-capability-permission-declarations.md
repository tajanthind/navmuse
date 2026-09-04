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

RESOLVED from the audit (ticket 01) + brief §4/§5/§22:

- **Capabilities**: the brief's assumption of a capability registry with
  exported constants is false on current core (v0.3.1) — no `capabilities`
  manifest field, no `server.extension`/`similarity`/`recommendation`
  constants, and a manifest carrying a `capabilities` key currently fails to
  load (`PluginManifest(**raw)` TypeError). Decision: the upgraded plugin
  remains a **pure `server_extension`** and the canonical manifest must be
  made load-compatible with current core (align canonical fnack-plugins with
  the loadable vendored mirror: no `capabilities` key — or land the small
  forward-compat core parser change first). Do not invent capability IDs.
- **Permissions**: declare only what the code actually uses: `settings`
  (plugin + AudioMuse settings via `context.settings`) and `network`
  (AudioMuse outbound HTTP via `context.http`). Drop the current canonical
  `library:read` + `filesystem:music` unless streaming is moved behind
  `context.fs` (today `stream` uses `send_file` on `local_path`, so no
  filesystem permission is exercised; keep it that way). Note: core only
  enforces `filesystem:downloads` today — declarations are the honest
  contract, enforcement is a core-side concern (documented in ticket 01).
