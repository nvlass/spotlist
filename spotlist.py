#!/usr/bin/env python3
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

import auth
import cache
import playlist as pl
import spotify

logger = logging.getLogger(__name__)


def resolve_tracks(
    tracks: list[pl.Track],
    token: str,
    strict: bool,
    track_cache: dict,
) -> list[tuple[pl.Track, str | None]]:
    resolved = []
    for track in tracks:
        uri = cache.lookup(track_cache, track.title, track.artist)
        if uri is not None:
            logger.info("[CACHE] %s — %s", track.title, track.artist)
        else:
            query = f"{track.title} {track.artist}"
            uri = spotify.search_track(query, token)
            if uri is None:
                if strict:
                    logger.error("[NOT FOUND] %s — %s", track.title, track.artist)
                    sys.exit(1)
                logger.warning("[NOT FOUND] %s — %s", track.title, track.artist)
            else:
                cache.store(track_cache, track.title, track.artist, uri)
                logger.info("[OK] %s — %s", track.title, track.artist)
        resolved.append((track, uri))
    return resolved


def print_segment_log(playlist_def: pl.PlaylistDef, resolved: list[tuple[pl.Track, str | None]]):
    uri_map = {(t.title, t.artist): uri for t, uri in resolved}
    logger.info("--- Segment Summary ---")
    for seg in playlist_def.segments:
        found = sum(1 for t in seg.tracks if uri_map.get((t.title, t.artist)))
        total = len(seg.tracks)
        dur = f"  [{seg.duration_target}]" if seg.duration_target else ""
        label = seg.name if seg.name else "(default)"
        logger.info("  %s%s: %d/%d tracks resolved", label, dur, found, total)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="spotlist",
        description="Create a Spotify playlist from a .spotlist file.",
    )
    parser.add_argument("playlist_file", help="Path to the .spotlist definition file")
    parser.add_argument("--dry-run", action="store_true", help="Resolve tracks but do not create playlist")
    parser.add_argument("--strict", action="store_true", help="Abort if any track cannot be found")
    parser.add_argument("--segment-log", action="store_true", help="Print per-segment summary after creation")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--no-cache", action="store_true", help="Bypass the local track URI cache")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    try:
        playlist_def = pl.parse(args.playlist_file)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        sys.exit(1)

    logger.info("Playlist: %s", playlist_def.name)
    if playlist_def.description:
        logger.info("Description: %s", playlist_def.description)
    logger.info("Tracks: %d across %d segment(s)", len(playlist_def.all_tracks()), len(playlist_def.segments))

    try:
        session = auth.authenticate()
    except RuntimeError as exc:
        logger.error("Auth error: %s", exc)
        sys.exit(1)

    track_cache = {} if args.no_cache else cache.load()

    logger.info("Resolving tracks…")
    resolved = resolve_tracks(playlist_def.all_tracks(), session.token, args.strict, track_cache)

    if not args.no_cache:
        cache.save(track_cache)

    found_uris = [uri for _, uri in resolved if uri]
    skipped = len(resolved) - len(found_uris)

    if args.segment_log:
        print_segment_log(playlist_def, resolved)

    if args.dry_run:
        logger.info("[Dry run] Would add %d track(s) (skipping %d).", len(found_uris), skipped)
        for track, uri in resolved:
            logger.info("  %s — %s: %s", track.title, track.artist, uri or "NOT FOUND")
        return

    if not found_uris:
        logger.error("No tracks resolved. Nothing to create.")
        sys.exit(1)

    try:
        playlist_id = spotify.create_playlist(
            playlist_def.name,
            playlist_def.description,
            session.token,
        )
        spotify.add_tracks(playlist_id, found_uris, session.token)
    except RuntimeError as exc:
        logger.error("Spotify API error: %s", exc)
        sys.exit(1)

    playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
    logger.info("Done! Playlist created with %d track(s).", len(found_uris))
    if skipped:
        logger.info("(%d track(s) skipped — not found on Spotify)", skipped)
    logger.info(playlist_url)


if __name__ == "__main__":
    main()
