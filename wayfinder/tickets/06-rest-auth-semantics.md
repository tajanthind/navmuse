# Decide /rest authentication semantics for the upgraded plugin

Type: grilling
Status: resolved
Blocked by: 01, 03

## Question

How should the `/rest/*` implementation handle the Subsonic authentication
mechanisms (`u`, `p`, `t`, `s`, `v`, `c`, api-key style) against fnack's auth
model (brief §9)?

Fnack stays zero-required-auth by default. No mandatory login may be
introduced. The plugin must not create a parallel authentication database or
auth subsystem. The current plugin authenticates against fnack's M2M API key
via `context.library.get_api_key()` (password == API key, or
`md5(key+salt) == t`), and is open when no key is configured.

The wire spec (ticket 03) adds OS-level nuance: `apiKey` auth extension, error
codes 41–44, and required `v`/`c` params. Decide which schemes the plugin will
accept/emit, whether the OS `apiKey` param maps to fnack's API key, and what
the zero-auth open behavior should be (u/p/t/s present but ignored when no key
is set, vs strict rejection).

## Resolution

RESOLVED from the corrected live audit (ticket 01) + spec (ticket 03) + brief §9:

- **Zero-auth default nuance (live main)**: fnack v0.3.21 auto-creates the M2M
  API key at startup (`get_or_create_api_key()` in app init) and surfaces it in
  `/api/settings`. So after first boot a key normally EXISTS — the Subsonic
  plugin's "open when no key" branch applies only to the pre-first-key state
  or if the user clears the key. fnack itself stays zero-required-auth for
  human-facing pages; the `/rest/*` surface is key-gated once the key exists.
- The plugin reads the key via `context.library.get_api_key()` (library:read);
  it should NOT call get_or_create_api_key (that needs library:write and would
  mutate state — out of scope). Document that the client uses fnack's M2M key
  as the Subsonic password.
- Accept classic schemes against that key: `u` + `p` (plain, and `enc:` hex)
  OR `u` + `t`+`s` where `token = md5(key + salt)`. `u` accepted but not
  identity-checked (fnack has no user accounts); `v`/`c` accepted (ignored or
  minimally validated); `f` selects format.
- Per Standard OS v1 (ticket 13): also accept the OS `apiKey` param mapping to
  the same fnack key; return OS error codes 41–44 for unsupported/conflicting
  auth rather than only 40.
- No parallel auth DB, no per-user subsystem (brief §9 hard constraint). No
  auth state to clean up in plugin lifecycle.
