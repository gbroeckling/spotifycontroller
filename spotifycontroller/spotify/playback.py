"""Spotify playback control wrapper.

Thin wrapper around the spotipy client that exposes DJ-style operations:
play, pause, skip, seek, volume, queue management, and track search.
"""

from __future__ import annotations

import logging
from typing import Any

import spotipy

_LOGGER = logging.getLogger(__name__)


class SpotifyPlayback:
    """Controls Spotify playback on the active Spotify Connect device."""

    def __init__(self, client: spotipy.Spotify) -> None:
        self._sp = client

    # -- Transport --

    def play(self, uri: str | None = None, device_id: str | None = None) -> None:
        """Start or resume playback. Optionally play a specific track URI."""
        kwargs: dict[str, Any] = {}
        if device_id:
            kwargs["device_id"] = device_id
        if uri:
            kwargs["uris"] = [uri]
        self._sp.start_playback(**kwargs)

    def pause(self, device_id: str | None = None) -> None:
        kwargs: dict[str, Any] = {}
        if device_id:
            kwargs["device_id"] = device_id
        self._sp.pause_playback(**kwargs)

    def toggle_play(self, device_id: str | None = None) -> None:
        """Toggle between play and pause."""
        state = self.get_state()
        if state and state.get("is_playing"):
            self.pause(device_id)
        else:
            self.play(device_id=device_id)

    def next_track(self, device_id: str | None = None) -> None:
        self._sp.next_track(device_id=device_id)

    def previous_track(self, device_id: str | None = None) -> None:
        self._sp.previous_track(device_id=device_id)

    # -- Seek / position --

    def seek(self, position_ms: int, device_id: str | None = None) -> None:
        self._sp.seek_track(position_ms, device_id=device_id)

    def nudge(self, delta_ms: int, device_id: str | None = None) -> None:
        """Seek forward or backward relative to current position."""
        state = self.get_state()
        if state and state.get("progress_ms") is not None:
            new_pos = max(0, state["progress_ms"] + delta_ms)
            self.seek(new_pos, device_id)

    # -- Volume --

    def set_volume(self, percent: int, device_id: str | None = None) -> None:
        """Set volume (0-100)."""
        percent = max(0, min(100, percent))
        self._sp.volume(percent, device_id=device_id)

    # -- Queue --

    def queue_track(self, uri: str, device_id: str | None = None) -> None:
        """Add a track to the playback queue."""
        self._sp.add_to_queue(uri, device_id=device_id)

    # -- State --

    def get_state(self) -> dict[str, Any] | None:
        """Return current playback state, or None if nothing is active."""
        return self._sp.current_playback()  # type: ignore[no-any-return]

    def get_current_track(self) -> dict[str, Any] | None:
        """Return info about the currently playing track."""
        state = self.get_state()
        if state and state.get("item"):
            return state["item"]  # type: ignore[no-any-return]
        return None

    # -- Devices --

    def get_devices(self) -> list[dict[str, Any]]:
        """Return available Spotify Connect devices."""
        result = self._sp.devices()
        return result.get("devices", []) if result else []

    def transfer_playback(self, device_id: str, force_play: bool = False) -> None:
        """Move playback to a different Spotify Connect device."""
        self._sp.transfer_playback(device_id, force_play=force_play)

    # -- Search --

    def search_tracks(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for tracks. Returns a list of track dicts."""
        result = self._sp.search(q=query, type="track", limit=limit)
        if result and "tracks" in result:
            return result["tracks"]["items"]  # type: ignore[no-any-return]
        return []

    # -- Playlists --

    def get_user_playlists(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the current user's playlists."""
        result = self._sp.current_user_playlists(limit=limit)
        return result.get("items", []) if result else []

    def get_playlist_tracks(self, playlist_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Return tracks in a playlist."""
        result = self._sp.playlist_tracks(playlist_id, limit=limit)
        if result and "items" in result:
            return [item["track"] for item in result["items"] if item.get("track")]
        return []
