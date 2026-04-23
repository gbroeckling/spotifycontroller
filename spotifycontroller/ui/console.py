"""Console UI for SpotifyController.

Interactive terminal for controlling Spotify playback, Mixxx library
management, audio capture routing, and local audio engine.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spotifycontroller.engine.audio import AudioEngine
    from spotifycontroller.engine.mixer import Mixer
    from spotifycontroller.midi.listener import MidiListener
    from spotifycontroller.mixxx.audio_capture import AudioCapture
    from spotifycontroller.spotify.playback import SpotifyPlayback

_LOGGER = logging.getLogger(__name__)


def _format_time(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


def _print_status(mixer: Mixer, playback: SpotifyPlayback, audio_engine: AudioEngine | None) -> None:
    state = playback.get_state()
    print("\n=== SpotifyController Status ===")
    print(f"Active deck: {mixer.active_deck.name}  Crossfader: {mixer.crossfader}")

    for deck in (mixer.deck_a, mixer.deck_b):
        if deck.track:
            print(f"\n  Deck {deck.name}: {deck.track.name} — {deck.track.artist}")
            vol = deck.volume_percent()
            eq = f"{deck.eq_hi}/{deck.eq_mid}/{deck.eq_lo}"
            print(f"    Vol: {vol}%  Playing: {deck.is_playing}  EQ: {eq}")
        else:
            print(f"\n  Deck {deck.name}: (empty)")

    if audio_engine:
        for ad in (audio_engine.deck_a, audio_engine.deck_b):
            if ad.track:
                state_str = "PLAY" if ad.is_playing else "STOP"
                pos = _format_time(ad.position_ms)
                dur = _format_time(ad.duration_ms)
                print(f"\n  Audio {ad.name}: {ad.track.name} [{pos}/{dur}] {state_str}")

    if state and state.get("item"):
        item = state["item"]
        pos = _format_time(state.get("progress_ms", 0))
        dur = _format_time(item.get("duration_ms", 0))
        print(f"\n  Spotify: {item['name']} [{pos}/{dur}]")
    else:
        print("\n  Spotify: (no active playback)")
    print("================================\n")


def run_console(
    mixer: Mixer,
    playback: SpotifyPlayback,
    listener: MidiListener,
    audio_engine: AudioEngine | None = None,
    audio_capture: AudioCapture | None = None,
    mixxx_proc: subprocess.Popen | None = None,
) -> None:
    """Interactive command loop."""
    print("\nSpotifyController is running. Type 'help' for commands.\n")

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

        # ---- Exit ----
        if cmd in ("quit", "exit", "q"):
            break

        # ---- Status ----
        elif cmd == "status":
            _print_status(mixer, playback, audio_engine)

        # ---- Spotify transport ----
        elif cmd == "play":
            playback.toggle_play()
        elif cmd == "pause":
            playback.pause()
        elif cmd == "next":
            playback.next_track()
            print("Next track.")
        elif cmd == "prev":
            playback.previous_track()
            print("Previous track.")
        elif cmd == "vol" and arg:
            try:
                playback.set_volume(int(arg))
            except ValueError:
                print("Usage: vol <0-100>")
        elif cmd == "seek" and arg:
            try:
                playback.seek(int(arg))
            except ValueError:
                print("Usage: seek <milliseconds>")

        # ---- Spotify browse ----
        elif cmd == "search" and arg:
            tracks = playback.search_tracks(arg, limit=8)
            for i, t in enumerate(tracks, 1):
                artists = ", ".join(a["name"] for a in t.get("artists", []))
                print(f"  {i}. {t['name']} — {artists}  [{_format_time(t.get('duration_ms', 0))}]")
        elif cmd == "devices":
            devices = playback.get_devices()
            if not devices:
                print("No Spotify Connect devices found.")
            else:
                for i, d in enumerate(devices, 1):
                    active = " *" if d.get("is_active") else ""
                    print(f"  {i}. {d['name']} ({d['type']}){active}")
        elif cmd == "playlists":
            pls = playback.get_user_playlists(limit=15)
            for i, p in enumerate(pls, 1):
                print(f"  {i}. {p['name']} ({p['tracks']['total']} tracks)")
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
                print("Nothing playing to load.")

        # ---- Mixxx library ----
        elif cmd == "import" and arg:
            _cmd_import(arg)
        elif cmd == "mixxx-search" and arg:
            _cmd_mixxx_search(arg)
        elif cmd == "crates":
            _cmd_list_crates()
        elif cmd == "install-mapping":
            from spotifycontroller.mixxx.integration import install_controller_mapping

            if install_controller_mapping():
                print("VCI-380 mapping installed. Restart Mixxx to activate.")
            else:
                print("Failed to install mapping.")
        elif cmd == "mixxx-status":
            from spotifycontroller.mixxx.integration import print_setup_status

            print_setup_status()
        elif cmd == "launch-mixxx":
            from spotifycontroller.mixxx.integration import find_mixxx_executable, launch_mixxx

            exe = find_mixxx_executable()
            if exe:
                proc = launch_mixxx(exe)
                if proc:
                    print(f"Mixxx launched (PID {proc.pid})")
            else:
                print("Mixxx not found.")

        # ---- Audio capture ----
        elif cmd == "capture" and arg:
            _cmd_capture(arg, audio_capture)
        elif cmd == "audio-devices":
            from spotifycontroller.mixxx.audio_capture import print_audio_routing_status

            print_audio_routing_status()

        # ---- Local audio engine ----
        elif cmd == "loadfile" and arg:
            _cmd_loadfile(arg, audio_engine)
        elif cmd == "aplay" and arg:
            _cmd_aplay(arg, audio_engine)
        elif cmd == "acf" and arg:
            if audio_engine is None:
                print("Audio engine not available.")
                continue
            try:
                audio_engine.crossfader = max(0.0, min(1.0, float(arg)))
                print(f"Audio crossfader: {audio_engine.crossfader:.2f}")
            except ValueError:
                print("Usage: acf <0.0-1.0>")

        # ---- Help ----
        elif cmd == "help":
            _print_help()
        else:
            print(f"Unknown: {cmd}. Type 'help'.")

    # Cleanup
    listener.stop()
    if audio_engine:
        audio_engine.stop()
    if audio_capture and audio_capture.is_running:
        audio_capture.stop()
    print("Goodbye.")
    sys.exit(0)


def _cmd_import(arg: str) -> None:
    """Import a folder into Mixxx's library."""
    parts = arg.split(maxsplit=1)
    folder = parts[0].strip('"').strip("'")
    crate_name = parts[1] if len(parts) > 1 else None

    path = Path(folder)
    if not path.is_dir():
        print(f"Not a directory: {folder}")
        return

    try:
        from spotifycontroller.mixxx.library import MixxxLibrary

        lib = MixxxLibrary()
        if crate_name:
            count = lib.import_folder_to_crate(path, crate_name)
            print(f"Imported {count} tracks into crate '{crate_name}'")
        else:
            count = lib.import_folder(path)
            print(f"Imported {count} tracks into Mixxx library")
        lib.close()
    except FileNotFoundError as e:
        print(str(e))


def _cmd_mixxx_search(query: str) -> None:
    """Search Mixxx's library."""
    try:
        from spotifycontroller.mixxx.library import MixxxLibrary

        lib = MixxxLibrary()
        results = lib.search_tracks(query, limit=10)
        if not results:
            print("No results in Mixxx library.")
        else:
            for i, t in enumerate(results, 1):
                bpm_str = f" {t.bpm:.0f}bpm" if t.bpm else ""
                print(f"  {i}. {t.title} — {t.artist}{bpm_str}")
        lib.close()
    except FileNotFoundError as e:
        print(str(e))


def _cmd_list_crates() -> None:
    """List Mixxx crates."""
    try:
        from spotifycontroller.mixxx.library import MixxxLibrary

        lib = MixxxLibrary()
        crates = lib.list_crates()
        if not crates:
            print("No crates.")
        else:
            for crate_id, name, count in crates:
                print(f"  {name} ({count} tracks)")
        lib.close()
    except FileNotFoundError as e:
        print(str(e))


def _cmd_capture(arg: str, audio_capture: AudioCapture | None) -> None:
    """Control audio capture."""
    if audio_capture is None:
        print("Audio capture not available.")
        return

    subcmd = arg.lower()
    if subcmd == "start":
        if audio_capture.start():
            print("Audio capture started.")
        else:
            print("Failed to start capture. Run 'audio-devices' to check setup.")
    elif subcmd == "stop":
        audio_capture.stop()
        print("Audio capture stopped.")
    elif subcmd == "status":
        print(f"Capture: {'running' if audio_capture.is_running else 'stopped'}")
    else:
        print("Usage: capture start|stop|status")


def _cmd_loadfile(arg: str, audio_engine: AudioEngine | None) -> None:
    """Load a local audio file onto an audio deck."""
    if audio_engine is None:
        print("Audio engine not available. pip install sounddevice soundfile")
        return

    parts = arg.split(maxsplit=1)
    if len(parts) < 2 or parts[0].upper() not in ("A", "B"):
        print("Usage: loadfile A|B <path>")
        return

    deck_id = parts[0].upper()
    file_path = Path(parts[1].strip('"').strip("'"))
    if audio_engine.load_file(deck_id, file_path):
        print(f"Audio Deck {deck_id}: loaded '{file_path.name}'")
    else:
        print(f"Failed to load: {file_path}")


def _cmd_aplay(arg: str, audio_engine: AudioEngine | None) -> None:
    """Toggle play on an audio deck."""
    if audio_engine is None:
        print("Audio engine not available.")
        return

    deck_id = arg.upper()
    if deck_id not in ("A", "B"):
        print("Usage: aplay A|B")
        return

    deck = audio_engine.deck_a if deck_id == "A" else audio_engine.deck_b
    deck.is_playing = not deck.is_playing
    print(f"Audio Deck {deck_id}: {'playing' if deck.is_playing else 'paused'}")


def _print_help() -> None:
    print("""
  --- Spotify ---
  play / pause / next / prev    transport controls
  vol <0-100>                   set volume
  seek <ms>                     seek to position
  search <query>                search Spotify
  load A|B                      load current track onto deck
  devices                       list Spotify Connect devices
  playlists                     list playlists

  --- Mixxx ---
  mixxx-status                  show Mixxx installation status
  install-mapping               install VCI-380 mapping into Mixxx
  launch-mixxx                  start Mixxx
  import <folder> [crate]       import audio files into Mixxx library
  mixxx-search <query>          search Mixxx library
  crates                        list Mixxx crates

  --- Audio Capture ---
  capture start|stop|status     WASAPI loopback capture
  audio-devices                 list audio devices + routing status

  --- Local Audio Engine ---
  loadfile A|B <path>           load audio file onto deck
  aplay A|B                     toggle play on audio deck
  acf <0.0-1.0>                 audio crossfader

  --- General ---
  status                        show all deck/playback info
  help                          this message
  quit                          exit
""")
