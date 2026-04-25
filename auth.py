import base64
import hashlib
import http.server
import json
import logging
import os
import secrets
import threading
import urllib.parse
import webbrowser

import requests

logger = logging.getLogger(__name__)

REDIRECT_URI = "http://127.0.0.1:8888/callback"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
SCOPES = "playlist-modify-public playlist-modify-private"


def _generate_pkce_pair():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _build_auth_url(client_id: str, challenge: str) -> str:
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def _wait_for_callback() -> str:
    """Spin up a one-shot HTTP server on :8888 and capture the auth code."""
    code_holder = {}
    ready = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if "error" in params:
                code_holder["error"] = params["error"][0]
            else:
                code_holder["code"] = params.get("code", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Authentication complete. You can close this tab.</h2></body></html>")
            ready.set()

        def log_message(self, *args):
            pass  # silence request logging

    server = http.server.HTTPServer(("localhost", 8888), Handler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    ready.wait(timeout=120)
    server.server_close()

    if "error" in code_holder:
        raise RuntimeError(f"Spotify auth error: {code_holder['error']}")
    if not code_holder.get("code"):
        raise RuntimeError("No auth code received — did you complete the browser login?")
    return code_holder["code"]


def _exchange_code(client_id: str, code: str, verifier: str) -> dict:
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "code_verifier": verifier,
        },
    )
    if not resp.ok:
        raise RuntimeError(f"Token exchange failed ({resp.status_code}): {resp.text}")
    return resp.json()


def _refresh_token(client_id: str, refresh_tok: str) -> dict:
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_tok,
            "client_id": client_id,
        },
    )
    if not resp.ok:
        raise RuntimeError(f"Token refresh failed ({resp.status_code}): {resp.text}")
    return resp.json()


class SpotifySession:
    """Holds in-memory token state for the lifetime of the process."""

    def __init__(self, token_data: dict, client_id: str):
        self._client_id = client_id
        self._access_token = token_data["access_token"]
        self._refresh_tok = token_data.get("refresh_token")

    @property
    def token(self) -> str:
        return self._access_token

    def refresh(self):
        if not self._refresh_tok:
            raise RuntimeError("No refresh token available.")
        data = _refresh_token(self._client_id, self._refresh_tok)
        self._access_token = data["access_token"]
        if "refresh_token" in data:
            self._refresh_tok = data["refresh_token"]


def authenticate() -> SpotifySession:
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    if not client_id:
        raise RuntimeError("SPOTIFY_CLIENT_ID is not set. Copy .env.example → .env and fill it in.")

    verifier, challenge = _generate_pkce_pair()
    auth_url = _build_auth_url(client_id, challenge)

    logger.info("Opening Spotify login in your browser…")
    webbrowser.open(auth_url)
    logger.info("Waiting for callback on http://127.0.0.1:8888/callback …")

    code = _wait_for_callback()
    token_data = _exchange_code(client_id, code, verifier)
    return SpotifySession(token_data, client_id)
