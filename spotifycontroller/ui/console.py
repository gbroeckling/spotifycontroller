"""Console UI for SpotifyController.

Provides a simple interactive terminal interface for status display
and manual commands while the MIDI listener runs in the background.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spotifycontroller.engine.mixer import Mixer
    from spotifycontroller.midi.listener import MidiListener
    from spotifycontroller.spotify.playback import SpotifyPlayback

_LOGGER = logging.getLogger(__name__)


def print_status(mixer: Mixer, playback: SpotifyPlayback) -> None:
    """Print current deck and playback status."""
    state = playback.get_state()
    print("\n=== SpotifyController Status ===")
    print(f"Active deck: {mixer.active_deck.name}")
    print(f"Crossfader:  {mixer.crossfader}")

    for deck in (mixer.deck_a, mixer.deck_b):
        if deck.track:
            print(f"\nDeck {deck.name}: {deck.track.name} — {deck.track.artist}")
            print(f"  Volume: {deck.volume_percent()}%  Playing: {deck.is_playing}")
            print(f"  EQ: hi={deck.eq_hi} mid={deck.eq_mid} lo={deck.eq_lo}")
            cues = ", ".join(f"{k}:{v}ms" for k, v in sorted(deck.cue_points.items()))
            if cues:
                print(f"  Cue points: {cues}")
        else:
            print(f"\nDeck {deck.name}: (empty)")

    if state and state.get("item"):
        item = state["item"]
        progress = state.get("progress_ms", 0)
        duration = item.get("duration_ms", 0)
        print(f"\nSpotify: {item['name']} [{progress // 1000}s / {duration // 1000}s]")
    else:
        print("\nSpotify: (no active playback)")

    print("================================\n")


def print_devices(playback: SpotifyPlayback) -> None:
    """List available Spotify Connect devices."""
    devices = playback.get_devices()
    if not devices:
        print("No Spotify Connect devices found.")
        return
    print("\nSpotify Connect devices:")
    for i, d in enumerate(devices, 1):
        active = " *" if d.get("is_active") else ""
        print(f"  {i}. {d['name']} ({d['type']}){active}")
    print()


def run_console(mixer: Mixer, playback: SpotifyPlayback, listener: MidiListener) -> None:
    """Interactive command loop."""
    print("\nSpotifyController is running.")
    print("MIDI listener:", "active" if listener.is_running else "NOT connected")
    print("\nCommands: status, devices, search <query>, load a|b, quit")
    print("Type 'help' for full command list.\n")

    while True:
        try:
            line = input("sc> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("quit", "exit", "q"):
            break
        elif cmd == "status":
            print_status(mixer, playback)
        elif cmd == "devices":
            print_devices(playback)
        elif cmd == "play":
            playback.toggle_play()
        elif cmd == "pause":
            playback.pause()
        elif cmd == "next":
            playback.next_track()
        elif cmd == "prev":
            playback.previous_track()
        elif cmd == "vol" and arg:
            try:
                playback.set_volume(int(arg))
            except ValueError:
                print("Usage: vol <0-100>")
        elif cmd == "search" and arg:
            tracks = playback.search_tracks(arg, limit=5)
            for i, t in enumerate(tracks, 1):
                artists = ", ".join(a["name"] for a in t.get("artists", []))
                print(f"  {i}. {t['name']} — {artists}  [{t['uri']}]")
        elif cmd == "load" and arg:
            deck_id = arg.upper()
            if deck_id not in ("A", "B"):
                print("Usage: load A|B")
                continue
            current = playback.get_current_track()
            if current:
                mixer.get_deck(deck_id).load_track(current)
                print(f"Loaded onto Deck {deck_id}")
            else:
                print("Nothing playing in Spotify to load.")
        elif cmd == "playlists":
            pls = playback.get_user_playlists(limit=10)
            for i, p in enumerate(pls, 1):
                print(f"  {i}. {p['name']} ({p['tracks']['total']} tracks)")
        elif cmd == "help":
            print("  status     — show deck and playback info")
            print("  devices    — list Spotify Connect devices")
            print("  play       — toggle play/pause")
            print("  pause      — pause playback")
            print("  next       — skip to next track")
            print("  prev       — previous track")
            print("  vol <0-100> — set volume")
            print("  search <q> — search for tracks")
            print("  load A|B   — load current track onto deck")
            print("  playlists  — list your playlists")
            print("  quit       — exit")
        else:
            print(f"Unknown command: {cmd}. Type 'help' for commands.")

    listener.stop()
    print("Goodbye.")
    sys.exit(0)
