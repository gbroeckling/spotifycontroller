"""Virtual DJ deck backed by Spotify playback.

Each deck holds a reference to a loaded track and manages transport state
for that track. Since Spotify only supports a single active playback stream,
the mixer coordinates which deck is "live" at any given time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

_LOGGER = logging.getLogger(__name__)


@dataclass
class TrackInfo:
    """Snapshot of a Spotify track loaded onto a deck."""

    uri: str
    name: str
    artist: str
    duration_ms: int
    album: str = ""
    artwork_url: str = ""

    @classmethod
    def from_spotify(cls, data: dict[str, Any]) -> TrackInfo:
        """Build from a Spotify track dict."""
        artists = ", ".join(a["name"] for a in data.get("artists", []))
        album = data.get("album", {})
        images = album.get("images", [])
        return cls(
            uri=data["uri"],
            name=data["name"],
            artist=artists,
            duration_ms=data["duration_ms"],
            album=album.get("name", ""),
            artwork_url=images[0]["url"] if images else "",
        )


@dataclass
class Deck:
    """A virtual DJ deck."""

    name: str  # "A" or "B"
    track: TrackInfo | None = None
    is_playing: bool = False
    volume: int = 100  # 0-127 (MIDI range), mapped to 0-100 for Spotify
    eq_hi: int = 64
    eq_mid: int = 64
    eq_lo: int = 64
    cue_points: dict[int, int] = field(default_factory=dict)  # pad_number -> position_ms

    @property
    def is_loaded(self) -> bool:
        return self.track is not None

    def load_track(self, track_data: dict[str, Any]) -> None:
        """Load a Spotify track onto this deck."""
        self.track = TrackInfo.from_spotify(track_data)
        self.is_playing = False
        self.cue_points.clear()
        _LOGGER.info("Deck %s: loaded '%s' by %s", self.name, self.track.name, self.track.artist)

    def set_cue_point(self, pad: int, position_ms: int) -> None:
        """Store a cue point for a hot-cue pad."""
        self.cue_points[pad] = position_ms
        _LOGGER.info("Deck %s: cue %d set at %d ms", self.name, pad, position_ms)

    def volume_percent(self) -> int:
        """Convert MIDI 0-127 volume to 0-100 percent."""
        return round(self.volume * 100 / 127)
