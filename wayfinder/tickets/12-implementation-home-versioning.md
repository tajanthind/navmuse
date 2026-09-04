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

RESOLVED from audit (ticket 01) + fnack ecosystem conventions + brief §29/§30:

- **Canonical edit target**: `tajanthind/fnack-plugins` →
  `plugins/fnack.subsonic/` (the single source of truth for plugin code,
  versioning, and index.json metadata).
- **Workflow** (recorded, not executed from this tracker): edit in
  fnack-plugins on a focused branch → run `python3 package_plugins.py`
  (zips + sha256 + regenerates index.json) → run the parity guard
  `python3 tests/test_manifest_index_parity.py` → commit/push + PR in
  fnack-plugins → vendor the updated plugin files into
  `fnack/bundled_plugins/fnack.subsonic/` → tag the core fnack release.
  fnack core must be able to load the shipped manifest (see ticket 04:
  either drop the `capabilities` key or land the tolerant parser first).
- **Versioning**: keep `api_version: ^1.0` (fnack plugin API 1.x unchanged);
  bump the plugin version from 1.0.0 per fnack-plugins conventions (the new
  feature surface warrants a minor+ bump; the exact number follows repo
  convention at execution time). `min_core_version`: only raise if the
  implementation uses a core API introduced after 0.3.1 — the cover-art core
  addition (ticket 16) is the only candidate; otherwise keep 0.2.0.
- **Do not push directly to fnack main** — use branches/PRs (fnack's
  established contribution model per its wayfinder docs).
