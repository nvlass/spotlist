import re
from dataclasses import dataclass, field


@dataclass
class Track:
    title: str
    artist: str
    segment: str = ""


@dataclass
class Segment:
    name: str
    duration_target: str = ""
    tracks: list[Track] = field(default_factory=list)


@dataclass
class PlaylistDef:
    name: str
    description: str
    segments: list[Segment]

    def all_tracks(self) -> list[Track]:
        return [track for seg in self.segments for track in seg.tracks]


def parse(path: str) -> PlaylistDef:
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    name = ""
    description = ""
    segments: list[Segment] = []
    current_segment: Segment | None = None

    for raw in lines:
        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        # [playlist] header
        if line == "[playlist]":
            current_segment = None
            continue

        # [segment: Name] header
        seg_match = re.match(r"^\[segment:\s*(.+)\]$", line)
        if seg_match:
            current_segment = Segment(name=seg_match.group(1).strip())
            segments.append(current_segment)
            continue

        # key = value pairs
        kv_match = re.match(r"^(\w+)\s*=\s*(.+)$", line)
        if kv_match:
            key, value = kv_match.group(1), kv_match.group(2).strip()
            if current_segment is None:
                # playlist-level metadata
                if key == "name":
                    name = value
                elif key == "description":
                    description = value
            else:
                if key == "duration_target":
                    current_segment.duration_target = value
            continue

        # track line: - Title | Artist
        track_match = re.match(r"^-\s+(.+?)\s*\|\s*(.+)$", line)
        if track_match:
            title, artist = track_match.group(1).strip(), track_match.group(2).strip()
            seg_name = current_segment.name if current_segment else ""
            track = Track(title=title, artist=artist, segment=seg_name)
            if current_segment is not None:
                current_segment.tracks.append(track)
            else:
                # tracks outside a segment go into an implicit default segment
                if not segments or segments[-1].name != "":
                    segments.append(Segment(name=""))
                segments[-1].tracks.append(track)
            continue

    if not name:
        raise ValueError(f"Playlist file '{path}' is missing a name under [playlist].")

    return PlaylistDef(name=name, description=description, segments=segments)
