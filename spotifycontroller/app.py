"""Main application entry point for SpotifyController.

Wires together the MIDI listener, Spotify client, virtual decks, audio
engine, and mixer, then drops into the console UI.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from spotifycontroller.engine.mixer import Mixer
from spotifycontroller.midi.listener import MidiListener, list_midi_ports
from spotifycontroller.midi.vestax_vci380 import VestaxVCI380
from spotifycontroller.spotify.auth import create_spotify_client
from spotifycontroller.spotify.playback import SpotifyPlayback
from spotifycontroller.ui.console import run_console

_LOGGER = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="spotifycontroller",
        description="DJ controller bridge for Spotify",
    )
    parser.add_argument(
        "--midi-port",
        default=None,
        help="MIDI input port name (auto-detects if omitted)",
    )
    parser.add_argument(
        "--list-midi",
        action="store_true",
        help="List available MIDI ports and exit",
    )
    parser.add_argument(
        "--midi-monitor",
        action="store_true",
        help="Print raw MIDI messages from your controller (for mapping verification)",
    )
    parser.add_argument(
        "--client-id",
        default=None,
        help="Spotify app client ID (or set SPOTIPY_CLIENT_ID env var)",
    )
    parser.add_argument(
        "--client-secret",
        default=None,
        help="Spotify app client secret (or set SPOTIPY_CLIENT_SECRET env var)",
    )
    parser.add_argument(
        "--no-audio-engine",
        action="store_true",
        help="Disable the local audio engine (Spotify-API-only mode)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # -- List MIDI ports --
    if args.list_midi:
        ports = list_midi_ports()
        if ports:
            print("Available MIDI input ports:")
            for p in ports:
                print(f"  - {p}")
        else:
            print("No MIDI input ports found.")
        sys.exit(0)

    # -- MIDI monitor mode --
    if args.midi_monitor:
        from spotifycontroller.midi.monitor import run_monitor

        run_monitor(port_name=args.midi_port)
        sys.exit(0)

    # -- Spotify credentials --
    client_id = args.client_id or os.environ.get("SPOTIPY_CLIENT_ID")
    client_secret = args.client_secret or os.environ.get("SPOTIPY_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("ERROR: Spotify credentials required.")
        print("Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment variables,")
        print("or pass --client-id and --client-secret.")
        print("\nCreate an app at https://developer.spotify.com/dashboard")
        sys.exit(1)

    # -- Authenticate with Spotify --
    print("Authenticating with Spotify...")
    sp_client = create_spotify_client(client_id, client_secret)
    playback = SpotifyPlayback(sp_client)

    # -- Audio engine (optional) --
    audio_engine = None
    if not args.no_audio_engine:
        try:
            from spotifycontroller.engine.audio import AUDIO_ENGINE_AVAILABLE, AudioEngine

            if AUDIO_ENGINE_AVAILABLE:
                audio_engine = AudioEngine()
                audio_engine.start()
                print("Local audio engine: ACTIVE (load local files with 'loadfile')")
            else:
                print("Local audio engine: DISABLED (install sounddevice + soundfile to enable)")
        except Exception:
            _LOGGER.debug("Audio engine init failed", exc_info=True)
            print("Local audio engine: DISABLED (optional)")

    # -- Controller setup --
    controller = VestaxVCI380()
    _LOGGER.info("Controller: %s (%s)", controller.mapping.name, controller.mapping.vendor)

    # -- Mixer --
    mixer = Mixer(controller, playback)
    mixer.bind()

    # -- MIDI listener --
    listener = MidiListener(controller, port_name=args.midi_port)
    ports = list_midi_ports()
    if ports:
        print(f"MIDI ports found: {', '.join(ports)}")
        listener.start()
    else:
        print("WARNING: No MIDI ports found. Running without controller input.")
        print("You can still use console commands to control Spotify.")

    # -- Console UI --
    run_console(mixer, playback, listener, audio_engine=audio_engine)


if __name__ == "__main__":
    main()
