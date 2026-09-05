"""Standalone tests for the fnack.subsonic plugin (plain python, no pytest,
no network). Runs against a stub fnack plugin API so nothing outside this repo
is required except Flask.

Run:
    /home/tajanthind/fnack/.venv/bin/python tests/test_subsonic_plugin.py
"""

import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

# --- build a stub `plugins` package (fnack API is read-only ground truth) --
_STUB = tempfile.mkdtemp(prefix="fnack_subsonic_stub_")
_PKG = os.path.join(_STUB, "plugins")
os.makedirs(_PKG)
with open(os.path.join(_PKG, "__init__.py"), "w") as fh:
    fh.write("")
with open(os.path.join(_PKG, "base.py"), "w") as fh:
    fh.write(
        "import abc\n"
        "class PluginBase(abc.ABC):\n"
        "    def __init__(self, context):\n"
        "        self.context = context\n"
        "    def on_load(self):\n        pass\n"
        "class ServerExtensionPlugin(PluginBase):\n"
        "    @abc.abstractmethod\n"
        "    def register_routes(self, blueprint):\n        ...\n"
    )
sys.path.insert(0, _STUB)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PLUGIN_DIR = os.path.join(_REPO_ROOT, "plugins", "fnack.subsonic")
sys.path.insert(0, _PLUGIN_DIR)  # `plugin` + sibling `audiomuse_client`

import flask  # noqa: E402
from plugins.base import ServerExtensionPlugin  # noqa: E402,F401 (stub)
import plugin as subsonic  # noqa: E402
from audiomuse_client import AudioMuseClient  # noqa: E402


# ---------------------------------------------------------------------------
# Stub fnack context
# ---------------------------------------------------------------------------

class FakeHTTPResponse:
    def __init__(self, status_code=200, payload=None, reason="OK"):
        self.status_code = status_code
        self._payload = payload
        self.reason = reason

    def json(self):
        return self._payload


class FakeHTTP:
    """Records calls; scripted responses per URL path."""

    def __init__(self):
        self.calls = []
        self.responses = {}   # path -> FakeHTTPResponse
        self.default = FakeHTTPResponse(200, [])

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers,
                           "timeout": timeout})
        for path, resp in self.responses.items():
            if url.rstrip("/").endswith(path):
                return resp
        return self.default


class FakeLibrary:
    def __init__(self, key=""):
        self._key = key
        self.artists = {1: {"id": 1, "name": "Alpha", "image_url": None},
                        2: {"id": 2, "name": "Beta", "image_url": None}}
        self.albums = {10: {"id": 10, "name": "First", "year": 2001,
                            "artist_id": 1, "cover_url": None,
                            "is_downloaded": True},
                       20: {"id": 20, "name": "Second", "year": 2002,
                            "artist_id": 2, "cover_url": None,
                            "is_downloaded": True}}
        self.tracks = {
            100: {"id": 100, "title": "Alpha One", "album_id": 10,
                  "artist_id": 1, "track_number": 1, "disc_number": 1,
                  "duration": 240, "file_path": None, "local_path": None,
                  "is_downloaded": True, "bitrate": 900, "size_bytes": 1234},
            101: {"id": 101, "title": "Alpha Two", "album_id": 10,
                  "artist_id": 1, "track_number": 2, "disc_number": 1,
                  "duration": 250, "file_path": None, "local_path": None,
                  "is_downloaded": True, "bitrate": 900, "size_bytes": 2345},
            200: {"id": 200, "title": "Beta One", "album_id": 20,
                  "artist_id": 2, "track_number": 1, "disc_number": 1,
                  "duration": 260, "file_path": None, "local_path": None,
                  "is_downloaded": True, "bitrate": 900, "size_bytes": 3456},
        }
        self.album_order = [[10, 20], [10, 20]]

    # -- permissions stub (live core enforces; stub is permissive) ---------
    def get_api_key(self):
        return self._key

    def get_artist(self, artist_id):
        return self.artists.get(artist_id)

    def get_album(self, album_id):
        return self.albums.get(album_id)

    def get_track(self, track_id):
        return self.tracks.get(track_id)

    def list_artists(self):
        return list(self.artists.values())

    def list_albums(self, artist_id=None, limit=None):
        out = [a for a in self.albums.values()
               if artist_id is None or a["artist_id"] == artist_id]
        return out[:limit] if limit else out

    def list_tracks(self, album_id=None, limit=None):
        out = [t for t in self.tracks.values()
               if album_id is None or t["album_id"] == album_id]
        return out[:limit] if limit else out


class FakeSettings:
    def __init__(self):
        self.data = {"enabled": "true", "audiomuse_enabled": "false",
                     "audiomuse_base_url": "", "audiomuse_api_key": ""}

    def get(self, key, default=None):
        return self.data.get(key, default)


class FakeContext:
    def __init__(self, http=None, key=""):
        self.library = FakeLibrary(key=key)
        self.settings = FakeSettings()
        self.http = http or FakeHTTP()


def make_app(context, url_prefix=""):
    app = flask.Flask(__name__)
    bp = flask.Blueprint("subsonic_test", __name__, url_prefix=url_prefix)
    plugin = subsonic.SubsonicPlugin(context)
    plugin.register_routes(bp)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app


def parse_xml(text):
    return ET.fromstring(text)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class EnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.app = make_app(FakeContext())

    def test_ping_xml_ok(self):
        r = self.app.test_client().get("/rest/ping.view")
        self.assertEqual(r.status_code, 200)
        self.assertIn("xml", r.content_type)
        root = parse_xml(r.data)
        self.assertEqual(root.tag, "{http://subsonic.org/restapi}subsonic-response")
        self.assertEqual(root.get("status"), "ok")
        self.assertEqual(root.get("version"), "1.16.1")
        self.assertEqual(root.get("openSubsonic"), "true")
        self.assertEqual(root.get("type"), "fnack")

    def test_ping_json_ok(self):
        r = self.app.test_client().get("/rest/ping?f=json")
        body = json.loads(r.data)
        env = body["subsonic-response"]
        self.assertEqual(env["status"], "ok")
        self.assertEqual(env["version"], "1.16.1")
        self.assertIs(env["openSubsonic"], True)

    def test_ping_wrong_format_default_xml(self):
        r = self.app.test_client().get("/rest/ping?f=xml")
        parse_xml(r.data)  # well-formed


class AuthTests(unittest.TestCase):
    def test_open_when_no_key(self):
        app = make_app(FakeContext())
        r = app.test_client().get("/rest/ping")
        self.assertEqual(r.status_code, 200)

    def test_wrong_password_40(self):
        ctx = FakeContext(key="sekret")
        app = make_app(ctx)
        r = app.test_client().get("/rest/ping?u=x&p=wrong")
        root = parse_xml(r.data)
        self.assertEqual(root.get("status"), "failed")
        err = root.find("{http://subsonic.org/restapi}error")
        self.assertEqual(int(err.get("code")), 40)

    def test_plain_password_ok(self):
        ctx = FakeContext(key="sekret")
        app = make_app(ctx)
        r = app.test_client().get("/rest/ping?u=x&p=sekret")
        root = parse_xml(r.data)
        self.assertEqual(root.get("status"), "ok")

    def test_enc_password_ok(self):
        ctx = FakeContext(key="sekret")
        app = make_app(ctx)
        enc = "enc:" + "sekret".encode().hex()
        r = app.test_client().get(f"/rest/ping?u=x&p={enc}")
        root = parse_xml(r.data)
        self.assertEqual(root.get("status"), "ok")

    def test_token_salt_ok(self):
        import hashlib
        ctx = FakeContext(key="sekret")
        app = make_app(ctx)
        s = "abcdef"
        t = hashlib.md5(("sekret" + s).encode()).hexdigest()
        r = app.test_client().get(f"/rest/ping?u=x&t={t}&s={s}")
        self.assertEqual(parse_xml(r.data).get("status"), "ok")

    def test_apikey_param_ok(self):
        ctx = FakeContext(key="sekret")
        app = make_app(ctx)
        r = app.test_client().get("/rest/ping?apiKey=sekret")
        self.assertEqual(parse_xml(r.data).get("status"), "ok")

    def test_conflicting_schemes_43(self):
        ctx = FakeContext(key="sekret")
        app = make_app(ctx)
        r = app.test_client().get("/rest/ping?u=x&p=sekret&apiKey=sekret")
        root = parse_xml(r.data)
        self.assertEqual(root.get("status"), "failed")
        self.assertEqual(int(root.find("{http://subsonic.org/restapi}error").get("code")), 43)

    def test_disabled_0(self):
        ctx = FakeContext()
        ctx.settings.data["enabled"] = "false"
        app = make_app(ctx)
        r = app.test_client().get("/rest/getMusicFolders")
        root = parse_xml(r.data)
        self.assertEqual(root.get("status"), "failed")
        self.assertEqual(int(root.find("{http://subsonic.org/restapi}error").get("code")), 0)


class BrowsingTests(unittest.TestCase):
    def setUp(self):
        self.client = make_app(FakeContext()).test_client()

    def test_getMusicFolders(self):
        r = self.client.get("/rest/getMusicFolders")
        root = parse_xml(r.data)
        mf = root.find("{http://subsonic.org/restapi}musicFolders")
        self.assertIsNotNone(mf)
        self.assertEqual(mf.find("{http://subsonic.org/restapi}musicFolder").get("name"), "Music")

    def test_getArtists_indexed(self):
        r = self.client.get("/rest/getArtists")
        root = parse_xml(r.data)
        artists = root.find("{http://subsonic.org/restapi}artists")
        idx = artists.findall("{http://subsonic.org/restapi}index")
        letters = [i.get("name") for i in idx]
        self.assertIn("A", letters)
        self.assertIn("B", letters)

    def test_getArtist(self):
        r = self.client.get("/rest/getArtist?id=ar-1")
        root = parse_xml(r.data)
        artist = root.find("{http://subsonic.org/restapi}artist")
        self.assertEqual(artist.get("name"), "Alpha")
        albums = artist.findall("{http://subsonic.org/restapi}album")
        self.assertEqual(len(albums), 1)
        self.assertEqual(albums[0].get("songCount"), "2")

    def test_getAlbum_songs(self):
        r = self.client.get("/rest/getAlbum?id=al-10")
        root = parse_xml(r.data)
        album = root.find("{http://subsonic.org/restapi}album")
        self.assertEqual(album.get("name"), "First")
        songs = album.findall("{http://subsonic.org/restapi}song")
        self.assertEqual(len(songs), 2)

    def test_getSong(self):
        r = self.client.get("/rest/getSong?id=tr-100")
        root = parse_xml(r.data)
        song = root.find("{http://subsonic.org/restapi}song")
        self.assertEqual(song.get("title"), "Alpha One")
        self.assertEqual(song.get("artist"), "Alpha")

    def test_missing_entity_70(self):
        r = self.client.get("/rest/getSong?id=tr-999")
        root = parse_xml(r.data)
        self.assertEqual(root.get("status"), "failed")
        self.assertEqual(int(root.find("{http://subsonic.org/restapi}error").get("code")), 70)

    def test_malformed_id_70(self):
        r = self.client.get("/rest/getSong?id=xyz")
        root = parse_xml(r.data)
        self.assertEqual(int(root.find("{http://subsonic.org/restapi}error").get("code")), 70)

    def test_getAlbumList2(self):
        r = self.client.get("/rest/getAlbumList2?type=newest&size=10")
        root = parse_xml(r.data)
        al = root.find("{http://subsonic.org/restapi}albumList2")
        self.assertEqual(len(al.findall("{http://subsonic.org/restapi}album")), 2)

    def test_search3(self):
        r = self.client.get("/rest/search3?query=Alpha")
        root = parse_xml(r.data)
        sr = root.find("{http://subsonic.org/restapi}searchResult3")
        self.assertEqual(len(sr.findall("{http://subsonic.org/restapi}artist")), 1)
        self.assertEqual(len(sr.findall("{http://subsonic.org/restapi}song")), 2)
        self.assertEqual(len(sr.findall("{http://subsonic.org/restapi}album")), 0)

    def test_search3_album_match(self):
        r = self.client.get("/rest/search3?query=First")
        root = parse_xml(r.data)
        sr = root.find("{http://subsonic.org/restapi}searchResult3")
        self.assertEqual(len(sr.findall("{http://subsonic.org/restapi}album")), 1)

    def test_search3_empty_query_returns_all(self):
        r = self.client.get("/rest/search3?query=")
        root = parse_xml(r.data)
        sr = root.find("{http://subsonic.org/restapi}searchResult3")
        self.assertEqual(len(sr.findall("{http://subsonic.org/restapi}artist")), 2)

    def test_getSimilarSongs_disabled_empty(self):
        r = self.client.get("/rest/getSimilarSongs?id=tr-100")
        root = parse_xml(r.data)
        sim = root.find("{http://subsonic.org/restapi}similarSongs")
        self.assertEqual(root.get("status"), "ok")
        self.assertEqual(len(sim.findall("{http://subsonic.org/restapi}song")), 0)

    def test_getArtistInfo_minimal(self):
        r = self.client.get("/rest/getArtistInfo?id=ar-1")
        root = parse_xml(r.data)
        ai = root.find("{http://subsonic.org/restapi}artistInfo")
        self.assertEqual(root.get("status"), "ok")
        self.assertEqual(ai.find("{http://subsonic.org/restapi}biography").text or "", "")

    def test_os_extensions(self):
        r = self.client.get("/rest/getOpenSubsonicExtensions")
        root = parse_xml(r.data)
        exts = root.find("{http://subsonic.org/restapi}openSubsonicExtensions")
        names = [e.get("name") for e in exts.findall("{http://subsonic.org/restapi}extension")]
        self.assertIn("apiKeyAuthentication", names)


class AudioMuseTests(unittest.TestCase):
    def test_similar_tracks_happy_path(self):
        http = FakeHTTP()
        http.responses["/api/similar_tracks"] = FakeHTTPResponse(200, [
            {"item_id": "tr-200", "title": "Beta One", "author": "Beta",
             "album": "Second", "distance": 0.2},
            {"item_id": "tr-101", "title": "Alpha Two", "author": "Alpha",
             "album": "First", "distance": 0.3},
            {"item_id": "tr-777", "title": "Ghost", "author": "Nobody",
             "album": "None", "distance": 0.5},  # unresolvable -> skipped
        ])
        ctx = FakeContext(http=http, key="sekret")
        ctx.settings.data.update({"audiomuse_enabled": "true",
                                  "audiomuse_base_url": "http://am:8000",
                                  "audiomuse_api_key": "tok"})
        app = make_app(ctx)
        r = app.test_client().get("/rest/getSimilarSongs2?id=tr-100&count=10&u=x&p=sekret")
        root = parse_xml(r.data)
        sim = root.find("{http://subsonic.org/restapi}similarSongs2")
        songs = sim.findall("{http://subsonic.org/restapi}song")
        self.assertEqual(root.get("status"), "ok")
        self.assertEqual(len(songs), 2)  # tr-200 + tr-101 resolved; tr-777 skipped
        # Bearer + n param sent
        call = http.calls[0]
        self.assertEqual(call["headers"].get("Authorization"), "Bearer tok")
        self.assertEqual(call["params"]["n"], 10)

    def test_audiomuse_down_falls_back_empty(self):
        http = FakeHTTP()
        http.default = FakeHTTPResponse(503, None, "Service Unavailable")
        ctx = FakeContext(http=http, key="sekret")
        ctx.settings.data.update({"audiomuse_enabled": "true",
                                  "audiomuse_base_url": "http://am:8000"})
        app = make_app(ctx)
        r = app.test_client().get("/rest/getSimilarSongs?id=tr-100&u=x&p=sekret")
        root = parse_xml(r.data)
        self.assertEqual(root.get("status"), "ok")  # never a server error
        sim = root.find("{http://subsonic.org/restapi}similarSongs")
        self.assertEqual(len(sim.findall("{http://subsonic.org/restapi}song")), 0)

    def test_disabled_no_http_call(self):
        http = FakeHTTP()
        ctx = FakeContext(http=http, key="sekret")
        ctx.settings.data.update({"audiomuse_enabled": "false",
                                  "audiomuse_base_url": "http://am:8000"})
        app = make_app(ctx)
        app.test_client().get("/rest/getSimilarSongs?id=tr-100&u=x&p=sekret")
        self.assertEqual(http.calls, [])  # zero AudioMuse calls


class ManifestTests(unittest.TestCase):
    def test_manifest_json(self):
        manifest_path = os.path.join(_REPO_ROOT, "plugins", "fnack.subsonic",
                                     "plugin.json")
        with open(manifest_path) as fh:
            m = json.load(fh)
        self.assertEqual(m["id"], "fnack.subsonic")
        self.assertEqual(m["type"], ["server_extension"])
        self.assertEqual(m["api_version"], "^1.0")
        self.assertEqual(m["capabilities"], ["server.extension"])
        self.assertIn("network", m["permissions"])
        self.assertIn("library:read", m["permissions"])
        keys = {s["key"] for s in m["settings_schema"]}
        self.assertIn("audiomuse_enabled", keys)
        self.assertIn("audiomuse_api_key", keys)
        secrets = [s for s in m["settings_schema"] if s["key"] == "audiomuse_api_key"]
        self.assertEqual(secrets[0]["type"], "secret")
        action_ids = [a["id"] for a in m["actions"]]
        self.assertIn("test-audiomuse-connection", action_ids)


class ArchitectureTests(unittest.TestCase):
    """Brief §24 architecture guard: the plugin never imports fnack internals."""

    def _plugin_source(self):
        with open(os.path.join(_PLUGIN_DIR, "plugin.py")) as fh:
            return fh.read()

    def test_no_forbidden_imports(self):
        src = self._plugin_source()
        for forbidden in ("import models", "from models",
                          "import db", "from db",
                          "import app", "from app",
                          "import services", "from services",
                          "sqlalchemy", "sqlite3"):
            self.assertNotIn(forbidden, src,
                             f"plugin.py must not import/use {forbidden}")

    def test_uses_plugin_base_only(self):
        src = self._plugin_source()
        self.assertIn("from plugins.base import ServerExtensionPlugin", src)
        # the only outbound HTTP is through context.http
        self.assertNotIn("import requests", src)
        self.assertNotIn("from requests", src)

    def test_audiomuse_module_no_network_bypass(self):
        with open(os.path.join(_PLUGIN_DIR, "audiomuse_client.py")) as fh:
            src = fh.read()
        self.assertIn("self.http.get", src)   # goes through context.http
        self.assertNotIn("socket", src)


class ActionTests(unittest.TestCase):
    def test_connection_action_disabled_reports(self):
        ctx = FakeContext(http=FakeHTTP())
        plugin = subsonic.SubsonicPlugin(ctx)
        out = plugin.test_audiomuse_connection()
        self.assertFalse(out["ok"])
        self.assertIn("disabled", out["message"])

    def test_connection_action_ok(self):
        http = FakeHTTP()
        http.responses["/api/health"] = FakeHTTPResponse(200, {"ok": True})
        ctx = FakeContext(http=http)
        ctx.settings.data.update({"audiomuse_enabled": "true",
                                  "audiomuse_base_url": "http://am:8000"})
        plugin = subsonic.SubsonicPlugin(ctx)
        out = plugin.test_audiomuse_connection()
        self.assertTrue(out["ok"])
        self.assertEqual(len(http.calls), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
