# Decide the implementation home + versioning + release workflow

Type: task
Status: resolved
Blocked by: 01

## Question

Where does the upgraded Subsonic plugin implementation land, and how is it
versioned and shipped (brief §29, §30)?

fnack's ecosystem convention (recorded in fnack's own wayfinder map "Decisions
so far") is: `tajanthind/fnack-plugins` is the canonical source of truth for
plugin code and catalog metadata; `fnack/bundled_plugins/` is a vendored
mirror kept in sync before tagging core releases. The brief §30 says to bump
the Subsonic plugin version per current conventions, keep `api_version: ^1.0`
(unless the repo proves a newer major), and only raise `min_core_version` if
an introduced API requires a newer fnack.

This ticket records the concrete execution workflow (branch/PR in
fnack-plugins, package_plugins.py + index.json regen, vendoring into fnack,
plugin version bump) so a future implementation session follows it. This
tracker does NOT make changes to fnack/fnack-plugins — it only records the
plan.

## Resolution

RESOLVED from the corrected live audit (ticket 01) + fnack ecosystem
conventions + brief §29/§30:

- **Canonical edit target**: `tajanthind/fnack-plugins` →
  `plugins/fnack.subsonic/` (single source of truth for plugin code,
  versioning, index.json). On live main the vendored
  `fnack/bundled_plugins/fnack.subsonic/` mirror is currently in sync with
  canonical (no drift) — keep it that way.
- **Workflow** (recorded, not executed from this tracker): edit in
  fnack-plugins on a focused branch → `python3 package_plugins.py` (zip +
  sha256 + index.json) → parity guard `python3
  tests/test_manifest_index_parity.py` → commit/push + PR in fnack-plugins →
  vendor the updated plugin files into `fnack/bundled_plugins/fnack.subsonic/`
  → tag the core fnack release. fnack core v0.3.21 loads the current manifest
  fine (`capabilities` + `actions` are supported — no parser workarounds
  needed, unlike the stale v0.3.1 core).
- **Versioning**: keep `api_version: ^1.0` (fnack plugin API 1.x unchanged —
  PLUGIN_API_VERSION is still 1.0.0); bump the plugin version from 1.0.0 per
  fnack-plugins conventions (minor+ for the new feature surface; exact number
  chosen at execution time). `min_core_version`: current value 0.2.0 predates
  permission enforcement and capabilities/actions — the upgraded plugin
  depends on core ≥ the release that introduced enforced permissions,
  secret-at-rest, and the capability registry, so raise it to the fnack core
  version that ships with those (v0.3.21-era or later), matching the repo's
  conventions at execution.
- **Do not push directly to fnack main** — branches + PRs (fnack's
  established model). fnack.subsonic is marketplace-official, NOT in
  Docker-essential set (plugins/essential.py) — no essential-list change
  needed; the bundled mirror stays for image compat.
