import requests

API_BASE = "https://api.spotify.com/v1"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _check(resp: requests.Response, context: str):
    if not resp.ok:
        raise RuntimeError(f"{context} failed ({resp.status_code}): {resp.text}")


def search_track(query: str, token: str) -> str | None:
    """Return the URI of the best-matching track, or None if not found."""
    resp = requests.get(
        f"{API_BASE}/search",
        headers=_headers(token),
        params={"q": query, "type": "track", "limit": 1},
    )
    _check(resp, f"Search for '{query}'")
    items = resp.json().get("tracks", {}).get("items", [])
    if not items:
        return None
    return items[0]["uri"]


def get_user_id(token: str) -> str:
    resp = requests.get(f"{API_BASE}/me", headers=_headers(token))
    _check(resp, "Get current user")
    return resp.json()["id"]


def create_playlist(user_id: str, name: str, description: str, token: str) -> str:
    """Create a playlist and return its ID."""
    resp = requests.post(
        f"{API_BASE}/users/{user_id}/playlists",
        headers=_headers(token),
        json={"name": name, "description": description, "public": False},
    )
    _check(resp, f"Create playlist '{name}'")
    return resp.json()["id"]


def add_tracks(playlist_id: str, track_uris: list[str], token: str):
    """Add tracks in batches of 100 (Spotify API limit)."""
    for i in range(0, len(track_uris), 100):
        batch = track_uris[i : i + 100]
        resp = requests.post(
            f"{API_BASE}/playlists/{playlist_id}/tracks",
            headers=_headers(token),
            json={"uris": batch},
        )
        _check(resp, f"Add tracks (batch starting at {i})")
