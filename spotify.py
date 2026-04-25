import logging
import time

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.spotify.com/v1"
_MAX_RETRIES = 3


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _request(method: str, url: str, context: str, **kwargs) -> requests.Response:
    for attempt in range(_MAX_RETRIES):
        resp = requests.request(method, url, **kwargs)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 2 ** attempt))
            logger.warning("Rate limited — waiting %ds before retry (%d/%d)…", wait, attempt + 1, _MAX_RETRIES)
            time.sleep(wait)
            continue
        if not resp.ok:
            raise RuntimeError(f"{context} failed ({resp.status_code}): {resp.text}")
        return resp
    raise RuntimeError(f"{context} failed: exceeded {_MAX_RETRIES} retries after rate limiting.")


def search_track(query: str, token: str) -> str | None:
    """Return the URI of the best-matching track, or None if not found."""
    resp = _request(
        "GET", f"{API_BASE}/search",
        context=f"Search for '{query}'",
        headers=_headers(token),
        params={"q": query, "type": "track", "limit": 1},
    )
    items = resp.json().get("tracks", {}).get("items", [])
    if not items:
        return None
    return items[0]["uri"]


def create_playlist(name: str, description: str, token: str) -> str:
    """Create a playlist and return its ID."""
    resp = _request(
        "POST", f"{API_BASE}/me/playlists",
        context=f"Create playlist '{name}'",
        headers=_headers(token),
        json={"name": name, "description": description, "public": False},
    )
    return resp.json()["id"]


def add_tracks(playlist_id: str, track_uris: list[str], token: str):
    """Add tracks in batches of 100 (Spotify API limit)."""
    for i in range(0, len(track_uris), 100):
        batch = track_uris[i : i + 100]
        _request(
            "POST", f"{API_BASE}/playlists/{playlist_id}/items",
            context=f"Add tracks (batch starting at {i})",
            headers=_headers(token),
            json={"uris": batch},
        )
