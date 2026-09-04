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

RESOLVED from audit (ticket 01) + spec (ticket 03) + brief §9:

- **Keep zero-auth-by-default.** When no fnack M2M API key is configured
  (`context.library.get_api_key() == ""`), `/rest/*` stays open — matching
  fnack's zero-required-auth model. (Existing behavior preserved.)
- When a key IS configured, accept the classic schemes against that single key:
  `u` + `p` (plain, and `enc:` hex per spec) OR `u` + `t`+`s` where
  `token = md5(key + salt)`. `u` is accepted but not identity-checked (fnack
  has no user accounts — document this); `v`/`c` accepted and ignored (or
  minimally validated), `f` selects format.
- Per the Standard OS v1 decision (ticket 13): also accept the OS `apiKey`
  param mapping to the same fnack key; return OS error codes 41–44 for
  unsupported/conflicting auth rather than only 40.
- No parallel auth DB, no per-user subsystem — the fnack M2M key remains the
  single credential (brief §9 hard constraint).
- Plugin lifecycle: no auth state to clean up; nothing at import/startup.
