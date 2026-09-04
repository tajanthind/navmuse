# Decide the enabled-by-default + route-gating semantics of the Subsonic plugin

Type: grilling
Status: resolved
Blocked by: 01

## Question

Should the upgraded Subsonic plugin be enabled by default in fnack, and should
the `enabled` manifest setting actually gate `/rest/*` route registration or
request handling?

Current state (observed in fnack-plugins `plugins/fnack.subsonic`): the
manifest's `settings_schema` has `enabled` default `false`, but the plugin
registers its routes unconditionally and the comment says "the enabled flag is
stored but not yet gating route registration (pre-existing behavior, unchanged
here)". Meanwhile the AudioMuse side must default off regardless
(`audiomuse_enabled=false`, brief §16).

Real-world consequence: a Subsonic-compatible server that is installed but
"disabled" by default while still answering `/rest/*` could surprise users who
expect the plugin page toggle to control exposure. Decide:
(a) keep current semantics (routes always active; `enabled` cosmetic);
(b) gate routes/requests on `enabled` and flip the default to `true` for new
   installs so the plugin works out of the box (recommended);
(c) gate on `enabled` and keep default `false` (opt-in exposure).

Note: whatever is chosen must not change fnack's zero-auth model or break the
marketplace enable/disable lifecycle expectations found in the audit (ticket
01).

## Resolution

RESOLVED by user decision: **gate on `enabled` and flip the default to
`true`**. The upgraded plugin's `settings_schema` `enabled` boolean (default
now `true`) becomes behaviorally meaningful — when the plugin is disabled in
the fnack plugins UI, `/rest/*` does not serve (either routes are not
registered at boot or requests return a disabled error), and a fresh install
works out of the box. This changes the pre-existing quirk where the checkbox
was cosmetic and routes answered regardless; existing installs that stored
`enabled=false` under the old cosmetic semantics must be migrated on upgrade
(read as enabled unless the user explicitly disabled after upgrade — an
implementation detail for ticket 12's session). AudioMuse remains independently
default-off via `audiomuse_enabled` (ticket 08) — gating the Subsonic server
and gating AudioMuse are separate toggles. Core note (ticket 01): fnack core
already skips route registration for disabled ServerExtensionPlugins at boot,
so this is largely a manifest-default + doc change plus verifying the
marketplace lifecycle honors it.
