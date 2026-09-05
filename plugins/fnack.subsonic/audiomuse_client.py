"""AudioMuse-AI client + normalized translation layer (fnack.subsonic plugin).

Kept as a sibling module so AudioMuse-specific JSON field names never leak
into the Subsonic route layer (brief §19 translation rule):

    AudioMuse response  ->  SimilarTrack (normalized)  ->  Subsonic <song>

The real AudioMuse HTTP contract (verified from its source, see
navmuse/wayfinder/research/02-audiomuse-http-api.md):

    GET {base}/api/similar_tracks?item_id=<id>&n=<count>
        Authorization: Bearer <api_key>          (only when a key is set)
        200 -> JSON array of rows:
        {"item_id","title","author","album","distance",
         "mood_vector","other_features","top_genre","top_mood","album_artist"}
        400/404/500 on unknown track/server, 503 when the index is empty.

Failure handling lives HERE, not in the route layer: any transport or
parse failure returns an empty result + reason, never an exception (fnack
auto-disables plugins after repeated failures; external-service errors must be
converted into normal fallback behavior, brief §6/§20).
"""

from __future__ import annotations

import logging
from typing import List, Optional

log = logging.getLogger("fnack.plugin.fnack.subsonic.audiomuse")

# Reasonable explicit timeout for every AudioMuse call (brief §15).
REQUEST_TIMEOUT_SECONDS = 10.0


class SimilarTrack:
    """Normalized sonic-similarity result (minimum fields for Subsonic).

    `ref_id` is the resolved fnack Subsonic track id (e.g. "tr-123") when the
    caller can map it; otherwise None and the caller falls back to matching
    by title/author in fnack's own library.
    """

    __slots__ = ("ref_id", "title", "author", "album", "distance")

    def __init__(self, ref_id: Optional[str], title: str, author: str = "",
                 album: str = "", distance: Optional[float] = None):
        self.ref_id = ref_id
        self.title = title or ""
        self.author = author or ""
        self.album = album or ""
        self.distance = distance

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (f"SimilarTrack(ref_id={self.ref_id!r}, title={self.title!r}, "
                f"author={self.author!r}, album={self.album!r})")


class AudioMuseResult:
    """Outcome of a similarity lookup: `ok` rows or a soft failure reason."""

    __slots__ = ("tracks", "ok", "reason")

    def __init__(self, tracks: Optional[List[SimilarTrack]] = None,
                 ok: bool = True, reason: str = ""):
        self.tracks = tracks or []
        self.ok = ok
        self.reason = reason

    def __repr__(self) -> str:  # pragma: no cover
        return (f"AudioMuseResult(ok={self.ok}, reason={self.reason!r}, "
                f"tracks={len(self.tracks)})")


class AudioMuseClient:
    """Thin, defensive client for AudioMuse-AI's similarity API.

    Uses the plugin's `context.http` (a preconfigured requests.Session) — the
    plugin never does raw networking (brief §15). All calls get an explicit
    timeout; all failures are converted to AudioMuseResult(ok=False, reason).
    """

    def __init__(self, base_url: str, api_key: str,
                 http_session, timeout: float = REQUEST_TIMEOUT_SECONDS):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.http = http_session
        self.timeout = timeout

    # -- similarity ---------------------------------------------------------

    def similar_tracks(self, item_id: str, count: int = 50,
                       title: str = "", author: str = "") -> AudioMuseResult:
        """Ask AudioMuse for sonic-similar tracks.

        Prefers reference by `item_id` (fnack's own Subsonic id, the shared
        id space when AudioMuse indexed fnack through a provider consuming
        fnack's Subsonic/OpenSubsonic endpoint). If the id lookup misses and
        title/author are provided, retry with the title+artist reference
        AudioMuse also accepts.
        """
        if not self.base_url:
            return AudioMuseResult(ok=False, reason="no base url configured")
        url = f"{self.base_url}/api/similar_tracks"
        params = {"n": int(count)}
        if item_id:
            params["item_id"] = item_id
        elif title or author:
            params["title"] = title
            params["artist"] = author
        else:
            return AudioMuseResult(ok=False, reason="no id or title to look up")
        resp = self._get(url, params)
        if not resp.ok:
            if not resp.error:
                return AudioMuseResult(ok=False, reason=resp.error)
            # id-based miss: retry title+artist once when we have strings
            if item_id and (title or author):
                params.pop("item_id", None)
                params["title"] = title
                params["artist"] = author
                retry = self._get(url, params)
                if not retry.ok:
                    return AudioMuseResult(ok=False, reason=retry.error)
                resp = retry
            else:
                return AudioMuseResult(ok=False, reason=resp.error)
        try:
            rows = resp.data
        except Exception as exc:  # pragma: no cover - defensive
            return AudioMuseResult(ok=False, reason=f"bad payload: {exc}")
        return self._normalize(rows)

    # -- connection test ----------------------------------------------------

    def test_connection(self) -> tuple:
        """Probe AudioMuse with a health call; returns (ok, message).

        GET /api/health is auth-exempt on AudioMuse (verified from source).
        """
        if not self.base_url:
            return False, "AudioMuse-AI base URL is not configured"
        resp = self._get(f"{self.base_url}/api/health", {})
        if resp.ok:
            return True, "AudioMuse-AI reachable"
        return False, resp.error

    # -- internals ----------------------------------------------------------

    def _headers(self) -> dict:
        headers = {"Accept": "application/json"}
        if self.api_key:
            # M2M auth on AudioMuse is a bearer API token (docs/AUTH.md).
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get(self, url: str, params: dict):
        """Perform a GET and normalize outcome. Never raises."""
        if self.http is None:
            return _Resp(False, data=None, error="no http session (network permission?)")
        try:
            r = self.http.get(url, params=params, headers=self._headers(),
                              timeout=self.timeout)
        except Exception as exc:  # connection refused/DNS/timeout/SSL
            return _Resp(False, data=None,
                         error=f"request failed: {type(exc).__name__}")
        if r.status_code >= 400:
            # 503 index empty/unavailable -> treat as soft failure (fallback)
            return _Resp(False, data=None,
                         error=f"http {r.status_code}: {r.reason}")
        try:
            return _Resp(True, data=r.json(), error="")
        except Exception:
            return _Resp(False, data=None, error="invalid JSON from AudioMuse")

    @staticmethod
    def _normalize(rows) -> AudioMuseResult:
        if rows is None:
            return AudioMuseResult(ok=False, reason="empty response")
        if not isinstance(rows, list):
            return AudioMuseResult(ok=False, reason="response is not a list")
        tracks: List[SimilarTrack] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            item_id = row.get("item_id")
            title = row.get("title")
            if not item_id and not title:
                continue  # malformed row: skip, not fatal
            tracks.append(SimilarTrack(
                ref_id=str(item_id) if item_id else None,
                title=str(title or ""),
                author=str(row.get("author") or ""),
                album=str(row.get("album") or ""),
                distance=row.get("distance"),
            ))
        return AudioMuseResult(tracks=tracks, ok=True, reason="")


class _Resp:
    """Tiny GET outcome holder (keeps AudioMuseClient dependency-free)."""

    __slots__ = ("ok", "data", "error")

    def __init__(self, ok: bool, data, error: str):
        self.ok = ok
        self.data = data
        self.error = error
