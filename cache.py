import json
import logging
import os

logger = logging.getLogger(__name__)

_DEFAULT_PATH = os.path.join(os.path.expanduser("~"), ".spotlist_cache.json")


def _key(title: str, artist: str) -> str:
    return f"{title.lower()}|{artist.lower()}"


def load(path: str = _DEFAULT_PATH) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("Loaded %d cached track(s) from %s", len(data), path)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read cache at %s: %s", path, exc)
        return {}


def save(cache: dict, path: str = _DEFAULT_PATH):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
        logger.debug("Saved %d cached track(s) to %s", len(cache), path)
    except OSError as exc:
        logger.warning("Could not write cache to %s: %s", path, exc)


def lookup(cache: dict, title: str, artist: str) -> str | None:
    return cache.get(_key(title, artist))


def store(cache: dict, title: str, artist: str, uri: str):
    cache[_key(title, artist)] = uri
