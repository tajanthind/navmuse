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

RESOLVED from audit (ticket 01) + AudioMuse research (ticket 02) + brief §21:

- fnack core (v0.3.1) has **no manifest `actions` mechanism** — nothing
  dispatches manifest actions to plugin methods, and the manifest parser
  rejects unknown keys. Adding one would require a core API addition, which is
  out of scope for this plugin upgrade and not required by the brief.
- Decision: **do not add a "Test AudioMuse-AI connection" action in v1.**
  Connection verification is covered by the failure/fallback behavior of
  ticket 09 (soft fail, documented) plus the automated mock tests of ticket
  15. If a manual test UX is wanted later, revisit only after fnack core
  supports manifest actions.
