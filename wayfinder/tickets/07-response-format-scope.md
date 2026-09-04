# Decide the response format scope (XML + JSON)

Type: grilling
Status: resolved
Blocked by: 03

## Question

Which wire format(s) should the upgraded Subsonic plugin emit (brief §7 lists
both "XML response structure" and "JSON response structure" among things to
inspect; the current plugin is JSON-only)?

The classic Subsonic spec defaults to XML (`f` param default `xml`) with `json`
available since 1.4.0; OpenSubsonic documents XML and JSON side by side and its
OpenAPI only allows `json` for its own docs. A server claiming classic
compatibility cannot be JSON-only.

## Resolution

RESOLVED by user decision + spec research (ticket 03): implement **both XML and
JSON**. Default format `xml` per the classic spec; honor `f=json` (and treat
`format=json` equivalently if present) for JSON output; keep the JSON wrapper
`{"subsonic-response": …}` and XML root attributes (`status`, `version`, and
OpenSubsonic `type`, `serverVersion`, `openSubsonic`) identical in meaning.
AudioMuse translation stays format-agnostic — only the route-layer serializer
differs.
