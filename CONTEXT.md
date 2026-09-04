# navmuse CONTEXT

This repo hosts wayfinder charts for music-infrastructure efforts around
`fnack` (self-hosted lossless downloader/library manager) and its plugin
ecosystem. Ground truth for terms below: the fnack/fnack-plugins repos, the
Subsonic/OpenSubsonic specs, and AudioMuse-AI's source.

## Language

**fnack**:
The self-hosted music downloader/library manager being extended.
_Avoid_: server, app

**fnack-plugins**:
The canonical repo for fnack's official plugin code, versioning, and catalog
metadata (`index.json`).
_Avoid_: bundled plugins, marketplace

**bundled mirror**:
`fnack/bundled_plugins/` — a vendored copy of canonical plugins kept in sync
before core releases; what the running core actually loads.
_Avoid_: canonical plugin source

**PluginContext**:
The compatibility boundary fnack plugins must interact through; exposes the
facades library, settings, events, http, fs, ui, jobs, log.
_Avoid_: direct imports of models/db/app/services

**ServerExtensionPlugin**:
The fnack plugin interface for plugins that contribute HTTP routes (e.g. a
Subsonic server) via `register_routes(blueprint)`.
_Avoid_: server_extension type confusion with capabilities

**Subsonic server** (fnack.subsonic):
The fnack plugin exposing the library as a Subsonic/OpenSubsonic `/rest/*` API
for clients like Symfonium/DSub/Sublime Music.
_Avoid_: Subsonic API (the spec), music server

**AudioMuse-AI**:
An external, separately deployed sonic-analysis service fnack optionally talks
to; never bundled or run by fnack.
_Avoid_: AudioMuse integration (the feature), the AudioMuse plugin

**AudioMuse-first, fnack-fallback**:
The similarity policy: use AudioMuse when it returns valid data; otherwise
return fnack's smallest valid response rather than an error.
_Avoid_: fail-hard, proxy-through

**M2M API key**:
fnack's single machine-to-machine credential (`context.library.get_api_key()`);
doubles as the Subsonic password/token secret. Empty key = zero-auth (open).
_Avoid_: user account, username
