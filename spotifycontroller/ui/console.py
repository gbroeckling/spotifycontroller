"""Console UI for SpotifyController.

Provides a simple interactive terminal interface for status display
and manual commands while the MIDI listener runs in the background.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spotifycontroller.engine.audio import AudioEngine
    from spotifycontroller.engine.mixer import Mixer
    from spotifycontroller.midi.listener import MidiListener
    from spotifycontroller.spotify.playback import SpotifyPlayback

_LOGGER = logging.getLogger(__name__)


def _format_time(ms: int) -> str:
    """Format milliseconds as m:ss."""
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


def print_status(mixer: Mixer, playback: SpotifyPlayback, audio_engine: AudioEngine | None) -> None:
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

    # Audio engine decks
    if audio_engine is not None:
        for ad in (audio_engine.deck_a, audio_engine.deck_b):
            if ad.track:
                pos = _format_time(ad.position_ms)
                dur = _format_time(ad.duration_ms)
                state_str = "PLAYING" if ad.is_playing else "stopped"
                print(f"\nAudio Deck {ad.name}: {ad.track.name} [{pos}/{dur}] {state_str}")
                print(f"  Volume: {ad.volume:.0%}  CF: {audio_engine.crossfader:.2f}")

    if state and state.get("item"):
        item = state["item"]
        progress = state.get("progress_ms", 0)
        duration = item.get("duration_ms", 0)
        print(f"\nSpotify: {item['name']} [{_format_time(progress)} / {_format_time(duration)}]")
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


def run_console(
    mixer: Mixer,
    playback: SpotifyPlayback,
    listener: MidiListener,
    audio_engine: AudioEngine | None = None,
) -> None:
    """Interactive command loop."""
    print("\nSpotifyController is running.")
    print("MIDI listener:", "active" if listener.is_running else "NOT connected")
    if audio_engine and audio_engine.is_running:
        print("Audio engine: active")
    print("\nCommands: status, play, pause, next, prev, devices, search, loadfile, quit")
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
            print_status(mixer, playback, audio_engine)
        elif cmd == "devices":
            print_devices(playback)
        elif cmd == "play":
            playback.toggle_play()
        elif cmd == "pause":
            playback.pause()
        elif cmd == "next":
            playback.next_track()
            print("Skipped to next track.")
        elif cmd == "prev":
            playback.previous_track()
            print("Back to previous track.")
        elif cmd == "vol" and arg:
            try:
                playback.set_volume(int(arg))
                print(f"Volume: {arg}%")
            except ValueError:
                print("Usage: vol <0-100>")
        elif cmd == "seek" and arg:
            try:
                ms = int(arg)
                playback.seek(ms)
                print(f"Seeked to {_format_time(ms)}")
            except ValueError:
                print("Usage: seek <milliseconds>")
        elif cmd == "search" and arg:
            tracks = playback.search_tracks(arg, limit=5)
            if not tracks:
                print("No results.")
            for i, t in enumerate(tracks, 1):
                artists = ", ".join(a["name"] for a in t.get("artists", []))
                dur = _format_time(t.get("duration_ms", 0))
                print(f"  {i}. {t['name']} — {artists}  [{dur}]  {t['uri']}")
        elif cmd == "load" and arg:
            deck_id = arg.upper()
            if deck_id not in ("A", "B"):
                print("Usage: load A|B")
                continue
            current = playback.get_current_track()
            if current:
                mixer.get_deck(deck_id).load_track(current)
                print(f"Loaded onto Deck {deck_id}: {current['name']}")
            else:
                print("Nothing playing in Spotify to load.")
        elif cmd == "loadfile" and arg:
            # loadfile A /path/to/song.mp3
            file_parts = arg.split(maxsplit=1)
            if len(file_parts) < 2 or file_parts[0].upper() not in ("A", "B"):
                print("Usage: loadfile A|B <path-to-audio-file>")
                continue
            if audio_engine is None:
                print("Audio engine not available. Install: pip install sounddevice soundfile")
                continue
            deck_id = file_parts[0].upper()
            file_path = Path(file_parts[1].strip('"').strip("'"))
            if audio_engine.load_file(deck_id, file_path):
                print(f"Audio Deck {deck_id}: loaded '{file_path.name}'")
            else:
                print(f"Failed to load: {file_path}")
        elif cmd == "aplay" and arg:
            # aplay A — play audio deck
            deck_id = arg.upper()
            if deck_id not in ("A", "B") or audio_engine is None:
                print("Usage: aplay A|B (requires audio engine)")
                continue
            deck = audio_engine.deck_a if deck_id == "A" else audio_engine.deck_b
            deck.is_playing = not deck.is_playing
            state = "playing" if deck.is_playing else "paused"
            print(f"Audio Deck {deck_id}: {state}")
        elif cmd == "acf" and arg:
            # acf 0.5 — set audio crossfader (0.0=A, 1.0=B)
            if audio_engine is None:
                print("Audio engine not available.")
                continue
            try:
                val = float(arg)
                audio_engine.crossfader = max(0.0, min(1.0, val))
                print(f"Audio crossfader: {audio_engine.crossfader:.2f}")
            except ValueError:
                print("Usage: acf <0.0-1.0>")
        elif cmd == "playlists":
            pls = playback.get_user_playlists(limit=10)
            for i, p in enumerate(pls, 1):
                print(f"  {i}. {p['name']} ({p['tracks']['total']} tracks)")
        elif cmd == "help":
            print("\n  --- Spotify Controls ---")
            print("  status       — show deck and playback info")
            print("  devices      — list Spotify Connect devices")
            print("  play         — toggle play/pause")
            print("  pause        — pause playback")
            print("  next         — skip to next track")
            print("  prev         — previous track")
            print("  vol <0-100>  — set volume")
            print("  seek <ms>    — seek to position in milliseconds")
            print("  search <q>   — search for tracks")
            print("  load A|B     — load current Spotify track onto virtual deck")
            print("  playlists    — list your playlists")
            print()
            print("  --- Local Audio Engine ---")
            print("  loadfile A|B <path> — load a local audio file onto audio deck")
            print("  aplay A|B           — toggle play/pause on audio deck")
            print("  acf <0.0-1.0>       — set audio crossfader (0=deck A, 1=deck B)")
            print()
            print("  quit  — exit")
            print()
        else:
            print(f"Unknown command: {cmd}. Type 'help' for commands.")

    listener.stop()
    if audio_engine is not None:
        audio_engine.stop()
    print("Goodbye.")
    sys.exit(0)
