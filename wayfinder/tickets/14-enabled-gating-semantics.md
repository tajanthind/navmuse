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

RESOLVED by user decision + corrected live audit (ticket 01): **gate on
`enabled`, default `true`** for the manifest setting.

Corrected mechanics on live fnack main v0.3.21:
- fnack already only registers server-extension `/rest/*` routes at boot for
  ENABLED plugins (capability registry: `providers(SERVER_EXTENSION)`); the
  per-plugin "enable" toggle in Settings → Plugins is the real gate, and
  bundled/official plugins auto-install enabled (except auth_provider).
- The plugin's `settings_schema` `enabled` boolean (default false) is a
  SEPARATE stored setting the plugin code currently never reads — that's the
  cosmetic quirk. Decision: flip its default to `true` AND make the plugin
  consult it (serve /rest only when the plugin is manager-enabled AND this
  setting is true), so a fresh install works out of the box and the two
  toggles don't contradict.
- Existing installs that stored `enabled=false` under the old cosmetic
  semantics must be migrated on upgrade (read as enabled unless the user
  explicitly disables after upgrade).
- AudioMuse stays independently default-off via `audiomuse_enabled` (ticket
  08) — Subsonic-server gating and AudioMuse gating are separate toggles.
