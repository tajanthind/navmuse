# Decide the AudioMuse settings schema (enabled, base URL, credential)

Type: grilling
Status: resolved
Blocked by: 02

## Question

What exactly goes into the upgraded plugin's `settings_schema` for the
AudioMuse integration (brief §14)?

The brief fixes most of this: `audiomuse_enabled` (boolean, default false,
label "Enable AudioMuse-AI integration"), `audiomuse_base_url` (string, default
"", label "AudioMuse-AI base URL", no hardcoded default unless verified from
the real AudioMuse repo). The open part is the credential: add a `secret`
setting (e.g. `audiomuse_api_key`) **only if** the real AudioMuse-AI API
actually uses an API key/token — never invent credentials. Depends on ticket
02's ground-truth of the AudioMuse HTTP API (auth requirements).

## Resolution

RESOLVED from AudioMuse research (ticket 02) + brief §14:

Final `settings_schema` additions to the EXISTING Subsonic plugin:

- `audiomuse_enabled` — boolean, default `false`, required `false`, display
  label "Enable AudioMuse-AI integration". No AudioMuse behavior of any kind
  when false.
- `audiomuse_base_url` — string, default `""`, required `false`, display label
  "AudioMuse-AI base URL". No hardcoded default (the verified default port is
  8000, but host is deployment-specific; compose maps ${FRONTEND_PORT:-8000}).
- `audiomuse_api_key` — **secret**, default `""`, required `false` — because
  the real AudioMuse API uses an optional `Authorization: Bearer <API_TOKEN>`
  header; send it only when non-empty. Never log it. (Verified from source —
  the credential is real, so the brief's conditional is satisfied.)

Settings stored via `context.settings` (per-plugin rows); the existing
`enabled` boolean setting stays as-is but becomes behaviorally meaningful per
ticket 14.
