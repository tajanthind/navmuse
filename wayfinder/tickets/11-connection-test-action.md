# Decide whether to add a "Test AudioMuse-AI connection" plugin action

Type: grilling
Status: resolved
Blocked by: 01, 02

## Question

Should the upgraded plugin declare a manifest `actions` entry such as
"Test AudioMuse-AI connection" (brief §21)?

The brief says: inspect whether the current plugin architecture supports an
appropriate connection-test action via the manifest's current `actions`
mechanism; add it only if useful and consistent with the existing Subsonic
plugin UX; it is not required for the feature; do not create a second UI
surface.

Resolution depends on ticket 01's audit of the real manifest `actions`
mechanism (does it exist, what does it invoke) and ticket 02 (what a useful
connection test would call).

## Resolution

RESOLVED after the corrected live audit (ticket 01) — fnack main v0.3.21
**does** support manifest `actions`: `PluginManifest.actions` is a real list
(each `{id, label}` renders as a button in the settings modal and maps to a
snake_cased method on the plugin instance), dispatched via
`POST /api/plugins/<id>/action/<action_id>` and guarded so only declared
actions run.

Decision: **add an optional "Test AudioMuse-AI connection" action** —
`{"id": "test-audiomuse-connection", "label": "Test AudioMuse-AI connection"}`
mapping to a plugin method that performs the same reachability call as ticket
09 (GET {base}/api/similar_tracks with a probe, or /api/health-equivalent per
ticket 02), returning a boolean + message shown in the settings modal. It is
optional (brief §21), fails soft, never blocks plugin load, and only appears
when AudioMuse settings are relevant (settings_schema still renders it; the
method no-ops/returns an explanatory message when disabled). No second UI
surface is created.
