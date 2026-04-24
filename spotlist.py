#!/usr/bin/env python3
import argparse
import sys

from dotenv import load_dotenv

import auth
import playlist as pl
import spotify


def resolve_tracks(
    tracks: list[pl.Track],
    token: str,
    strict: bool,
) -> list[tuple[pl.Track, str | None]]:
    resolved = []
    for track in tracks:
        query = f"{track.title} {track.artist}"
        uri = spotify.search_track(query, token)
        if uri is None:
            msg = f"  [NOT FOUND] {track.title} — {track.artist}"
            if strict:
                print(msg, file=sys.stderr)
                sys.exit(1)
            print(f"WARNING: {msg}")
        else:
            print(f"  [OK] {track.title} — {track.artist}")
        resolved.append((track, uri))
    return resolved


def print_segment_log(playlist_def: pl.PlaylistDef, resolved: list[tuple[pl.Track, str | None]]):
    uri_map = {(t.title, t.artist): uri for t, uri in resolved}
    print("\n--- Segment Summary ---")
    for seg in playlist_def.segments:
        found = sum(1 for t in seg.tracks if uri_map.get((t.title, t.artist)))
        total = len(seg.tracks)
        dur = f"  [{seg.duration_target}]" if seg.duration_target else ""
        label = seg.name if seg.name else "(default)"
        print(f"  {label}{dur}: {found}/{total} tracks resolved")


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
    args = parser.parse_args()

    # Parse playlist file
    try:
        playlist_def = pl.parse(args.playlist_file)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\nPlaylist: {playlist_def.name}")
    if playlist_def.description:
        print(f"Description: {playlist_def.description}")
    print(f"Tracks: {len(playlist_def.all_tracks())} across {len(playlist_def.segments)} segment(s)\n")

    # Authenticate
    try:
        session = auth.authenticate()
    except RuntimeError as exc:
        print(f"Auth error: {exc}", file=sys.stderr)
        sys.exit(1)

    print("\nResolving tracks…")
    resolved = resolve_tracks(playlist_def.all_tracks(), session.token, args.strict)

    found_uris = [uri for _, uri in resolved if uri]
    skipped = len(resolved) - len(found_uris)

    if args.segment_log:
        print_segment_log(playlist_def, resolved)

    if args.dry_run:
        print(f"\n[Dry run] Would add {len(found_uris)} track(s) (skipping {skipped}).")
        for track, uri in resolved:
            status = uri if uri else "NOT FOUND"
            print(f"  {track.title} — {track.artist}: {status}")
        return

    if not found_uris:
        print("No tracks resolved. Nothing to create.", file=sys.stderr)
        sys.exit(1)

    # Create playlist
    try:
        user_id = spotify.get_user_id(session.token)
        playlist_id = spotify.create_playlist(
            user_id,
            playlist_def.name,
            playlist_def.description,
            session.token,
        )
        spotify.add_tracks(playlist_id, found_uris, session.token)
    except RuntimeError as exc:
        print(f"Spotify API error: {exc}", file=sys.stderr)
        sys.exit(1)

    playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
    print(f"\nDone! Playlist created with {len(found_uris)} track(s).")
    if skipped:
        print(f"({skipped} track(s) skipped — not found on Spotify)")
    print(f"\n{playlist_url}")


if __name__ == "__main__":
    main()
