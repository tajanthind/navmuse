"""fnack first-party plugin: Subsonic/OpenSubsonic server extension (upgraded).

Implements the decision-complete plan in navmuse/wayfinder/map.md for the
brief "Subsonic-API compatibility + optional AudioMuse-AI integration".

Highlights vs the previous v1.0.0 first-cut:
- XML **and** JSON responses (classic default `f=xml`, `f=json` honored),
  plus OpenSubsonic envelope attrs (type/serverVersion/openSubsonic) and the
  OS `apiKey` auth param with OS error codes 41-44 (tickets 07/13/06).
- Full endpoint surface: ping, getLicense, getMusicFolders, getIndexes,
  getArtists, getArtist, getAlbum, getMusicDirectory, getAlbumList2, getSong,
  getCoverArt, stream, download, search3, getSimilarSongs(2),
  getArtistInfo(2), getScanStatus/startScan, getOpenSubsonicExtensions.
- Optional AudioMuse-AI sonic similarity (default off; strict
  AudioMuse-first, fnack-fallback semantics) via the sibling
  `audiomuse_client` module (tickets 02/08/09).
- Manifest `actions` entry "test-audiomuse-connection" (ticket 11).
- `enabled` setting default true and honored; permissions
  settings/library:read/network; capability server.extension (tickets 04/14).

Auth: zero-auth open only while no M2M key exists; otherwise clients
authenticate with fnack's M2M API key (u/p plain or enc: hex, u/t+s token
md5(key+salt), or OS apiKey param).

No transcoding (container has no ffmpeg): stream/download serve original
bytes; HTTP Range is handled by Flask's send_file(conditional=True).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import re
import time
from xml.sax.saxutils import escape

from flask import Blueprint, Response, request, send_file

from plugins.base import ServerExtensionPlugin

from audiomuse_client import AudioMuseClient

log = logging.getLogger("fnack.plugin.fnack.subsonic")

# ---------------------------------------------------------------------------
# Constants (wire contract from research/03-subsonic-wire-contract.md)
# ---------------------------------------------------------------------------

SUBSONIC_VERSION = "1.16.1"           # claimed protocol version
OS_TYPE = "fnack"                     # OS envelope: server name
OS_SERVER_VERSION = "0.3.21"          # fnack core this targets (min_core_version)
_NS = "http://subsonic.org/restapi"

_MIME = {
    ".flac": "audio/flac", ".opus": "audio/ogg", ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac",
    ".wav": "audio/wav", ".webm": "audio/webm",
}
_COVER_CANDIDATES = ("cover.jpg", "cover.png", "cover.webp", "folder.jpg",
                     "front.jpg", "album.jpg", "AlbumArtSmall.jpg")

_ID_RE = re.compile(r"^(ar|al|tr)-(\d+)$")


def _parse_id(raw, kind):
    """Parse a prefixed Subsonic id like tr-123. Returns int or None."""
    if not raw:
        return None
    m = _ID_RE.match(str(raw))
    if not m:
        return None
    return int(m.group(2)) if m.group(1) == kind else None


# ---------------------------------------------------------------------------
# Payload + serialization
#
# payload node = {field: value}:
#   scalar            -> XML attribute / JSON property
#   dict {"#text": s} -> XML child element with text / JSON string property
#   list              -> repeated XML child elements named field / JSON array
# `root_name=None` means an envelope-only response (e.g. ping).
# ---------------------------------------------------------------------------


def _esc_attr(v):
    return escape(str(v), {'"': "&quot;"})


def _node_xml(name, node):
    attrs, children = [], []
    for key, val in (node or {}).items():
        if val is None:
            continue
        if isinstance(val, dict) and set(val) == {"#text"}:
            children.append(f"<{key}>{escape(str(val['#text']))}</{key}>")
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    children.append(_node_xml(key, item))
                else:
                    children.append(f"<{key}>{escape(str(item))}</{key}>")
        elif isinstance(val, bool):
            attrs.append(f'{key}="{str(val).lower()}"')
        else:
            attrs.append(f'{key}="{_esc_attr(val)}"')
    attr_str = (" " + " ".join(attrs)) if attrs else ""
    child_str = "".join(children) if children else ""
    if not attr_str and not child_str:
        return f"<{name}/>"
    return f"<{name}{attr_str}>{child_str}</{name}>"


def _json_node(node):
    out = {}
    for key, val in (node or {}).items():
        if val is None:
            continue
        if isinstance(val, dict) and set(val) == {"#text"}:
            out[key] = val["#text"]
        elif isinstance(val, list):
            out[key] = [_json_node(i) if isinstance(i, dict) else i for i in val]
        else:
            out[key] = val
    return out


def _envelope(status="ok", error=None):
    env = {"status": status, "version": SUBSONIC_VERSION,
           "type": OS_TYPE, "serverVersion": OS_SERVER_VERSION,
           "openSubsonic": True}
    if error is not None:
        env["error"] = error
    return env


def _envelope_xml(status="ok", inner=""):
    return (f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<subsonic-response xmlns="{_NS}" status="{status}" '
            f'version="{SUBSONIC_VERSION}" type="{OS_TYPE}" '
            f'serverVersion="{OS_SERVER_VERSION}" openSubsonic="true">'
            f"{inner}</subsonic-response>")


def response_payload(root_name, node, fmt="xml", error=None, mimetype=None):
    """Build a subsonic-response. Errors: HTTP 200 + status=failed (wire
    contract). root_name None -> envelope only (ping)."""
    if error is not None:
        if fmt == "json":
            return _finish({"subsonic-response": _envelope("failed", error)},
                           fmt, mimetype)
        err = _node_xml("error", error)
        return _finish(_envelope_xml("failed", err), fmt, mimetype)
    if fmt == "json":
        payload = dict(_envelope())
        if root_name is not None:
            payload[root_name] = _json_node(node)
        return _finish({"subsonic-response": payload}, fmt, mimetype)
    inner = "" if root_name is None else _node_xml(root_name, node)
    return _finish(_envelope_xml("ok", inner), fmt, mimetype)


def _finish(body, fmt, mimetype=None):
    if fmt == "json":
        return Response(json.dumps(body), status=200,
                        mimetype=mimetype or "application/json")
    return Response(body, status=200, mimetype=mimetype or "application/xml")


# ---------------------------------------------------------------------------
# Plugin
# ---------------------------------------------------------------------------


class SubsonicPlugin(ServerExtensionPlugin):
    """Subsonic/OpenSubsonic REST server over fnack's library."""

    # -- shared request helpers --------------------------------------------

    def _fmt(self):
        f = (request.values.get("f") or request.values.get("format") or "xml")
        return "json" if f.lower() == "json" else "xml"

    def _enabled(self) -> bool:
        try:
            val = self.context.settings.get("enabled", "true")
        except Exception:
            return True
        return str(val).lower() != "false"

    def _api_key(self):
        try:
            return self.context.library.get_api_key() or ""
        except Exception:
            return ""

    def _scheme_count(self):
        """Count distinct auth schemes present (p, t+s, apiKey)."""
        args = request.values
        n = 0
        if args.get("p") is not None:
            n += 1
        if args.get("t") is not None or args.get("s") is not None:
            n += 1
        if args.get("apiKey") is not None:
            n += 1
        return n

    def _auth_ok(self) -> bool:
        """Classic u/p, u/t+s, or OS apiKey against fnack's M2M key."""
        key = self._api_key()
        if not key:
            return True  # zero-auth: no key configured = open
        args = request.values
        p, t, s = args.get("p"), args.get("t"), args.get("s")
        api_key = args.get("apiKey")
        if self._scheme_count() > 1:
            return False  # conflicting -> 43 by caller
        if api_key is not None:
            return api_key == key
        if p is not None:
            if str(p).startswith("enc:"):
                try:
                    p = bytes.fromhex(str(p)[4:]).decode("utf-8", "replace")
                except Exception:
                    return False
            return p == key
        if t is not None and s is not None:
            return hashlib.md5((key + s).encode()).hexdigest() == t
        return False

    def _gate(self):
        """Return an error Response when disabled/unauthenticated, else None."""
        if not self._enabled():
            return self._fail(0, "Subsonic server is disabled")
        if not self._auth_ok():
            if self._scheme_count() > 1:
                return self._fail(43, "Conflicting authentication schemes")
            return self._fail(40, "Wrong username or password")
        return None

    def _fail(self, code, message, binary=False):
        """Error response. On binary endpoints the spec wants a text/xml
        error body (stream/download/getCoverArt); other endpoints may use
        the format-selected XML or JSON envelope."""
        fmt = self._fmt()
        mime = None
        if binary and fmt != "json":
            mime = "text/xml"
        return response_payload(None, None, fmt=fmt, mimetype=mime,
                                error={"code": code, "message": message})

    def _ok(self, root_name, node):
        return response_payload(root_name, node, fmt=self._fmt())

    # -- fnack data -> Subsonic nodes --------------------------------------

    def _artist(self, artist_id):
        try:
            return self.context.library.get_artist(artist_id)
        except Exception:
            return None

    def _album(self, album_id):
        try:
            return self.context.library.get_album(album_id)
        except Exception:
            return None

    def _track(self, track_id):
        try:
            return self.context.library.get_track(track_id)
        except Exception:
            return None

    def _suffix(self, path):
        ext = os.path.splitext(str(path or ""))[1].lstrip(".").lower()
        return ext or None

    def _content_type(self, path):
        return _MIME.get(os.path.splitext(str(path or ""))[1].lower(),
                         "application/octet-stream")

    def _path_of(self, tr):
        return tr.get("local_path") or tr.get("file_path")

    def _artist_name(self, artist_id):
        art = self._artist(artist_id) if artist_id else None
        return (art or {}).get("name") or ""

    def _track_node(self, tr):
        path = self._path_of(tr)
        n = {
            "id": f"tr-{tr['id']}",
            "isDir": False,
            "title": tr.get("title") or "",
            "track": int(tr["track_number"]) if tr.get("track_number") else None,
            "discNumber": int(tr["disc_number"]) if tr.get("disc_number") else None,
            "duration": int(tr.get("duration") or 0),
            "albumId": f"al-{tr['album_id']}" if tr.get("album_id") else None,
            "artistId": f"ar-{tr['artist_id']}" if tr.get("artist_id") else None,
            "path": path,
            "size": int(tr["size_bytes"]) if tr.get("size_bytes") else None,
            "contentType": self._content_type(path),
            "suffix": self._suffix(path),
            "isVideo": False,
            "type": "music",
        }
        if tr.get("album_id"):
            alb = self._album(tr["album_id"])
            if alb:
                n["album"] = alb.get("name")
                if alb.get("year"):
                    n["year"] = int(alb["year"])
        if tr.get("artist_id"):
            name = self._artist_name(tr["artist_id"])
            if name:
                n["artist"] = name
        return {k: v for k, v in n.items() if v is not None}

    def _album_node(self, alb, with_songs=False, stats=None):
        """AlbumID3-style node. stats = {album_id: (songCount, durationMs)}"""
        songs, duration = [], 0
        if with_songs:
            try:
                tracks = self.context.library.list_tracks(album_id=alb["id"]) or []
            except Exception:
                tracks = []
            songs = [self._track_node(t) for t in tracks]
            duration = sum(int(t.get("duration") or 0) for t in tracks)
        elif stats and int(alb["id"]) in stats:
            duration = stats[int(alb["id"])][1]
        node = {
            "id": f"al-{alb['id']}",
            "name": alb.get("name") or "",
            "artist": self._artist_name(alb.get("artist_id")),
            "artistId": f"ar-{alb['artist_id']}" if alb.get("artist_id") else None,
            "year": int(alb["year"]) if alb.get("year") else None,
            "songCount": len(songs) if with_songs else
                         (stats[int(alb["id"])][0]
                          if stats and int(alb["id"]) in stats else 0),
            "duration": duration,
            "created": self._created(alb),
        }
        if with_songs:
            node["song"] = songs
        return {k: v for k, v in node.items() if v is not None}

    @staticmethod
    def _created(alb):
        year = alb.get("year")
        return (f"{int(year)}-01-01T00:00:00Z" if year
                else "1970-01-01T00:00:00Z")

    def _album_stats(self):
        """{album_id: (songCount, totalDuration)} from one library scan."""
        try:
            tracks = self.context.library.list_tracks(limit=100000) or []
        except Exception:
            tracks = []
        stats = {}
        for t in tracks:
            aid = t.get("album_id")
            if aid is None:
                continue
            aid = int(aid)
            cur = stats.get(aid, [0, 0])
            stats[aid] = [cur[0] + 1, cur[1] + int(t.get("duration") or 0)]
        return stats

    def _indexed_artists(self):
        """Group artists by index letter; albumCount from one album scan."""
        try:
            artists = self.context.library.list_artists() or []
        except Exception:
            artists = []
        try:
            albums = self.context.library.list_albums(limit=100000) or []
        except Exception:
            albums = []
        counts = {}
        for a in albums:
            if a.get("artist_id") is not None:
                aid = int(a["artist_id"])
                counts[aid] = counts.get(aid, 0) + 1
        from collections import defaultdict
        buckets = defaultdict(list)
        for a in artists:
            name = a.get("name") or ""
            letter = name[0].upper() if name and name[0].isalnum() else "#"
            buckets[letter].append({
                "id": f"ar-{a['id']}",
                "name": name,
                "albumCount": counts.get(int(a["id"]), 0),
            })
        return [{"name": letter,
                 "artist": sorted(v, key=lambda x: x["name"].lower())}
                for letter, v in sorted(buckets.items())]

    def _artist_albums(self, artist_id):
        try:
            return self.context.library.list_albums(artist_id=artist_id,
                                                    limit=100000) or []
        except Exception:
            return []

    def _all_albums(self):
        try:
            return self.context.library.list_albums(limit=100000) or []
        except Exception:
            return []

    def _all_tracks(self):
        try:
            return self.context.library.list_tracks(limit=100000) or []
        except Exception:
            return []

    def _all_artists(self):
        try:
            return self.context.library.list_artists() or []
        except Exception:
            return []

    # -- media file serving ------------------------------------------------

    def _serve_file(self, as_attachment: bool):
        """stream/download implementation (raw bytes, Range via send_file)."""
        track_id = _parse_id(request.values.get("id"), "tr")
        if track_id is None:
            return self._fail(70, "File not found", binary=True)
        tr = self._track(track_id)
        if not tr:
            return self._fail(70, "File not found", binary=True)
        path = self._path_of(tr)
        if not path or not os.path.isfile(str(path)):
            return self._fail(70, "File not found", binary=True)
        try:
            return send_file(str(path),
                             mimetype=self._content_type(path),
                             as_attachment=as_attachment,
                             download_name=os.path.basename(str(path))
                             if as_attachment else None,
                             conditional=True, max_age=0)
        except Exception as exc:  # pragma: no cover - fs edge cases
            log.warning("stream/download failed: %s", exc)
            return self._fail(70, "File unavailable", binary=True)

    def _cover_path(self, raw):
        """Locate a local cover image beside the first track of the entity.

        fnack's library facade does not yet expose cover-art bytes/paths
        (core API gap, wayfinder ticket 16); this is the transitional
        heuristic documented in the plugin README.
        """
        try:
            tracks = []
            if raw.startswith("tr-"):
                tid = _parse_id(raw, "tr")
                tr = self._track(tid) if tid else None
                tracks = [tr] if tr else []
            elif raw.startswith("al-"):
                aid = _parse_id(raw, "al")
                if aid is not None:
                    tracks = self.context.library.list_tracks(album_id=aid) or []
            elif raw.startswith("ar-"):
                aid = _parse_id(raw, "ar")
                albums = self._artist_albums(aid) if aid is not None else []
                if albums:
                    tracks = (self.context.library.list_tracks(
                        album_id=albums[0]["id"]) or [])
            else:
                return None
        except Exception:
            return None
        for tr in tracks:
            p = self._path_of(tr)
            if not p:
                continue
            d = os.path.dirname(str(p))
            for name in _COVER_CANDIDATES:
                cand = os.path.join(d, name)
                if os.path.isfile(cand):
                    return cand
        return None

    # -- AudioMuse ----------------------------------------------------------

    def _audiomuse(self):
        try:
            enabled = str(self.context.settings.get("audiomuse_enabled", "false"))
            base = (self.context.settings.get("audiomuse_base_url") or "").strip()
        except Exception:
            return None
        if enabled.lower() != "true" or not base:
            return None
        try:
            key = self.context.settings.get("audiomuse_api_key") or ""
        except Exception:
            key = ""
        return AudioMuseClient(base, key, self.context.http)

    def test_audiomuse_connection(self):
        """Manifest action 'test-audiomuse-connection' (ticket 11)."""
        client = self._audiomuse()
        if client is None:
            return {"ok": False,
                    "message": "AudioMuse-AI integration is disabled — enable "
                               "audiomuse_enabled and set audiomuse_base_url"}
        ok, msg = client.test_connection()
        return {"ok": ok, "message": msg}

    # -- AudioMuse similarity resolution ------------------------------------

    def _track_artist(self, tr):
        return self._artist_name(tr.get("artist_id")) if tr else ""

    def _resolve_similar(self, result, count):
        """AudioMuse rows -> fnack Subsonic <song> nodes (skip unknowns)."""
        songs = []
        for s in result.tracks:
            if len(songs) >= count:
                break
            node = None
            if s.ref_id:
                tid = _parse_id(s.ref_id, "tr")
                if tid:
                    tr = self._track(tid)
                    if tr:
                        node = self._track_node(tr)
            if node is None and s.title:
                node = self._match_track(s.title, s.author)
            if node:
                songs.append(node)
        return songs

    def _match_track(self, title, author):
        want = (title or "").strip().lower()
        for tr in self._all_tracks():
            if (tr.get("title") or "").strip().lower() != want:
                continue
            if author and tr.get("artist_id"):
                name = self._artist_name(tr["artist_id"])
                if name and name.strip().lower() != author.strip().lower():
                    continue
            return self._track_node(tr)
        return None

    # -- route registration -------------------------------------------------

    def register_routes(self, blueprint: Blueprint) -> None:
        bp = blueprint

        def add(path):
            """Register /rest/<path> and /rest/<path>.view (GET+POST)."""
            def deco(fn):
                bp.route(f"/rest/{path}", methods=["GET", "POST"])(fn)
                bp.route(f"/rest/{path}.view", methods=["GET", "POST"])(fn)
                return fn
            return deco

        def int_param(name, default):
            try:
                return max(int(request.values.get(name, default)), 0)
            except Exception:
                return default

        @add("ping")
        def ping():
            g = self._gate()
            if g:
                return g
            if self._fmt() == "json":
                return _finish({"subsonic-response": _envelope()}, "json")
            return _finish(_envelope_xml("ok"), "xml")

        @add("getLicense")
        def get_license():
            g = self._gate()
            if g:
                return g
            return self._ok("license", {
                "valid": True,
                "email": "fnack",
                "licenseExpires": "2035-01-01T00:00:00Z",
            })

        @add("getOpenSubsonicExtensions")
        def os_extensions():
            # OS: callable with no auth; advertise only what we implement.
            return self._ok("openSubsonicExtensions",
                            {"extension": [{"name": "apiKeyAuthentication"},
                                           {"name": "formPost"}]})

        @add("getScanStatus")
        def scan_status():
            g = self._gate()
            if g:
                return g
            return self._ok("scanStatus", {"scanning": False, "count": 0})

        @add("startScan")
        def start_scan():
            g = self._gate()
            if g:
                return g
            # fnack's facade exposes no scan trigger to server extensions;
            # honest no-op (documented in the plugin README).
            return self._ok("scanStatus", {"scanning": False, "count": 0})

        @add("getMusicFolders")
        def get_music_folders():
            g = self._gate()
            if g:
                return g
            return self._ok("musicFolders",
                            {"musicFolder": [{"id": 1, "name": "Music"}]})

        @add("getArtists")
        def get_artists():
            g = self._gate()
            if g:
                return g
            return self._ok("artists",
                            {"ignoredArticles": "", "index": self._indexed_artists()})

        @add("getIndexes")
        def get_indexes():
            g = self._gate()
            if g:
                return g
            return self._ok("indexes", {
                "lastModified": int(time.time() * 1000),
                "ignoredArticles": "",
                "index": self._indexed_artists(),
            })

        @add("getArtist")
        def get_artist():
            g = self._gate()
            if g:
                return g
            artist_id = _parse_id(request.values.get("id"), "ar")
            if artist_id is None:
                return self._fail(70, "Artist not found")
            art = self._artist(artist_id)
            if not art:
                return self._fail(70, "Artist not found")
            albums = self._artist_albums(artist_id)
            stats = self._album_stats()
            node = {"id": f"ar-{art['id']}", "name": art.get("name") or "",
                    "albumCount": len(albums),
                    "album": [self._album_node(a, stats=stats)
                              for a in albums]}
            return self._ok("artist", node)

        @add("getAlbum")
        def get_album():
            g = self._gate()
            if g:
                return g
            album_id = _parse_id(request.values.get("id"), "al")
            if album_id is None:
                return self._fail(70, "Album not found")
            alb = self._album(album_id)
            if not alb:
                return self._fail(70, "Album not found")
            return self._ok("album", self._album_node(alb, with_songs=True))

        @add("getSong")
        def get_song():
            g = self._gate()
            if g:
                return g
            track_id = _parse_id(request.values.get("id"), "tr")
            if track_id is None:
                return self._fail(70, "Song not found")
            tr = self._track(track_id)
            if not tr:
                return self._fail(70, "Song not found")
            # get_track() omits album/artist context (facade gap); the album
            # scan carries it, so enrich before building the Child node.
            if not tr.get("album_id"):
                for row in self._all_tracks():
                    if row["id"] == track_id:
                        tr = {**tr, **{k: row[k] for k in
                                        ("album_id", "artist_id",
                                         "track_number", "disc_number",
                                         "size_bytes", "is_downloaded")
                                        if k in row}}
                        break
            return self._ok("song", self._track_node(tr))

        @add("getMusicDirectory")
        def get_music_directory():
            g = self._gate()
            if g:
                return g
            raw = request.values.get("id") or "1"
            node = {"id": raw, "name": "Music", "child": []}
            if raw.startswith("al-"):
                album_id = _parse_id(raw, "al")
                alb = self._album(album_id) if album_id else None
                if not alb:
                    return self._fail(70, "Album not found")
                node["name"] = alb.get("name") or ""
                try:
                    tracks = self.context.library.list_tracks(album_id=album_id) or []
                except Exception:
                    tracks = []
                node["child"] = [self._track_node(t) for t in tracks]
            else:
                for alb in self._all_albums():
                    c = {"id": f"al-{alb['id']}", "isDir": True,
                         "title": alb.get("name") or "",
                         "year": int(alb["year"]) if alb.get("year") else None,
                         "artist": self._artist_name(alb.get("artist_id")),
                         "artistId": f"ar-{alb['artist_id']}"
                                     if alb.get("artist_id") else None}
                    node["child"].append({k: v for k, v in c.items()
                                          if v is not None})
            return self._ok("directory", node)

        @add("getAlbumList2")
        def get_album_list2():
            g = self._gate()
            if g:
                return g
            list_type = request.values.get("type", "alphabeticalByName")
            albums = list(self._all_albums())
            if list_type == "random":
                random.shuffle(albums)
            elif list_type == "newest":
                albums.sort(key=lambda a: a.get("id", 0), reverse=True)
            elif list_type == "byYear":
                year = int_param("fromYear", 0)
                albums = [a for a in albums
                          if int(a.get("year") or 0) == year]
            elif list_type == "alphabeticalByArtist":
                albums.sort(key=lambda a: str(a.get("name") or "").lower())
            else:  # alphabeticalByName, recent, starred -> alphabetical
                albums.sort(key=lambda a: str(a.get("name") or "").lower())
            size = min(int_param("size", 10), 500)
            offset = int_param("offset", 0)
            stats = self._album_stats()
            nodes = [self._album_node(a, stats=stats)
                     for a in albums[offset: offset + size]]
            return self._ok("albumList2", {"album": nodes})

        @add("search3")
        def search3():
            g = self._gate()
            if g:
                return g
            query = (request.values.get("query") or "").strip().lower()
            artist_count = int_param("artistCount", 20)
            album_count = int_param("albumCount", 20)
            song_count = int_param("songCount", 20)
            res = {"artist": [], "album": [], "song": []}
            if query:
                for a in self._all_artists():
                    if query in (a.get("name") or "").lower():
                        res["artist"].append({"id": f"ar-{a['id']}",
                                              "name": a.get("name") or ""})
                for alb in self._all_albums():
                    if query in (alb.get("name") or "").lower():
                        res["album"].append(self._album_node(alb))
                for tr in self._all_tracks():
                    if query in (tr.get("title") or "").lower():
                        res["song"].append(self._track_node(tr))
            else:  # OS: empty query returns data (offline sync support)
                res["artist"] = [{"id": f"ar-{a['id']}",
                                  "name": a.get("name") or ""}
                                 for a in self._all_artists()]
                res["album"] = [self._album_node(a) for a in self._all_albums()]
                res["song"] = [self._track_node(t) for t in self._all_tracks()]
            res["artist"] = res["artist"][:artist_count]
            res["album"] = res["album"][:album_count]
            res["song"] = res["song"][:song_count]
            return self._ok("searchResult3", res)

        @add("getSimilarSongs")
        def get_similar_songs():
            g = self._gate()
            if g:
                return g
            return self._similar_response("similarSongs")

        @add("getSimilarSongs2")
        def get_similar_songs2():
            g = self._gate()
            if g:
                return g
            return self._similar_response("similarSongs2")

        @add("getArtistInfo")
        def artist_info():
            g = self._gate()
            if g:
                return g
            return self._artist_info_response("artistInfo")

        @add("getArtistInfo2")
        def artist_info2():
            g = self._gate()
            if g:
                return g
            return self._artist_info_response("artistInfo2")

        @add("stream")
        def stream():
            g = self._gate()
            if g:
                return g
            return self._serve_file(as_attachment=False)

        @add("download")
        def download():
            g = self._gate()
            if g:
                return g
            return self._serve_file(as_attachment=True)

        @add("getCoverArt")
        def get_cover_art():
            g = self._gate()
            if g:
                return g
            path = self._cover_path(request.values.get("id") or "")
            if not path:
                return self._fail(70, "Cover not found", binary=True)
            try:
                mime = self._content_type(path)
                if not mime.startswith("image"):
                    mime = "image/jpeg"
                return send_file(str(path), mimetype=mime, conditional=True,
                                 max_age=0)
            except Exception as exc:  # pragma: no cover
                log.warning("getCoverArt failed: %s", exc)
                return self._fail(70, "Cover not found", binary=True)

    # -- similarity / artist-info shared bodies -----------------------------

    def _similar_response(self, root):
        count = int_param_clamped(self, "count", 50, 500)
        client = self._audiomuse()
        if client is None:
            # AudioMuse disabled/unconfigured: smallest valid response.
            return self._ok(root, {"song": []})
        track_id = _parse_id(request.values.get("id"), "tr")
        tr = self._track(track_id) if track_id else None
        result = client.similar_tracks(
            item_id=f"tr-{track_id}" if track_id else "",
            count=count,
            title=(tr or {}).get("title") or "",
            author=self._track_artist(tr))
        return self._ok(root, {"song": self._resolve_similar(result, count)})

    def _artist_info_response(self, root):
        # AudioMuse has no artist-info endpoint (research ticket 02):
        # minimal valid structure with fnack-side data only (ticket 10).
        return self._ok(root, {
            "biography": {"#text": ""},
            "musicBrainzId": {"#text": ""},
            "lastFmUrl": {"#text": ""},
            "smallImageUrl": {"#text": ""},
            "mediumImageUrl": {"#text": ""},
            "largeImageUrl": {"#text": ""},
            "similarArtist": [],
        })


def int_param_clamped(self, name, default, ceiling):
    try:
        return min(max(int(request.values.get(name, default)), 0), ceiling)
    except Exception:
        return default
