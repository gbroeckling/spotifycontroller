"""Main application entry point for SpotifyController.

Wires together Mixxx, MIDI listener, Spotify client, audio capture,
and the console UI.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from spotifycontroller.engine.mixer import Mixer
from spotifycontroller.midi.listener import MidiListener, list_midi_ports
from spotifycontroller.midi.vestax_vci380 import VestaxVCI380
from spotifycontroller.mixxx.integration import (
    find_mixxx_executable,
    install_controller_mapping,
    print_setup_status,
)
from spotifycontroller.spotify.auth import create_spotify_client
from spotifycontroller.spotify.playback import SpotifyPlayback
from spotifycontroller.ui.console import run_console

_LOGGER = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="spotifycontroller",
        description="DJ controller bridge — Spotify + Mixxx + VCI-380",
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
        "--setup",
        action="store_true",
        help="Show Mixxx + audio setup status and exit",
    )
    parser.add_argument(
        "--install-mapping",
        action="store_true",
        help="Install VCI-380 controller mapping into Mixxx and exit",
    )
    parser.add_argument(
        "--install-skin",
        action="store_true",
        help="Install Traktmixxx-RAW skin into Mixxx and exit",
    )
    parser.add_argument(
        "--install-all",
        action="store_true",
        help="Install both controller mapping and skin into Mixxx and exit",
    )
    parser.add_argument(
        "--launch-mixxx",
        action="store_true",
        help="Launch Mixxx after setup",
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

    # -- Setup status --
    if args.setup:
        print_setup_status()
        from spotifycontroller.mixxx.audio_capture import print_audio_routing_status

        print_audio_routing_status()
        sys.exit(0)

    # -- Install mapping --
    if args.install_mapping or args.install_all:
        if install_controller_mapping():
            print("VCI-380 mapping installed into Mixxx.")
            print("Restart Mixxx > Preferences > Controllers > Vestax VCI-380")
        else:
            print("Failed to install mapping.")
        if not args.install_all:
            sys.exit(0)

    # -- Install skin --
    if args.install_skin or args.install_all:
        from spotifycontroller.mixxx.integration import install_skin

        if install_skin():
            print("Traktmixxx-RAW skin installed into Mixxx.")
            print("Restart Mixxx > Preferences > Interface > select Traktmixxx-RAW")
        else:
            print("Failed to install skin.")
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

    # -- Mixxx status --
    mixxx_exe = find_mixxx_executable()
    if mixxx_exe:
        print(f"Mixxx found: {mixxx_exe}")
    else:
        print("Mixxx not found. Install from https://mixxx.org/download/")
        print("SpotifyController works without Mixxx but with limited DJ features.")

    # -- Launch Mixxx if requested --
    mixxx_proc = None
    if args.launch_mixxx and mixxx_exe:
        from spotifycontroller.mixxx.integration import launch_mixxx

        mixxx_proc = launch_mixxx(mixxx_exe)
        if mixxx_proc:
            print(f"Mixxx launched (PID {mixxx_proc.pid})")

    # -- Audio engine --
    audio_engine = None
    try:
        from spotifycontroller.engine.audio import AUDIO_ENGINE_AVAILABLE, AudioEngine

        if AUDIO_ENGINE_AVAILABLE:
            audio_engine = AudioEngine()
            audio_engine.start()
            print("Local audio engine: ACTIVE")
        else:
            print("Local audio engine: DISABLED (pip install sounddevice soundfile)")
    except Exception:
        _LOGGER.debug("Audio engine init failed", exc_info=True)

    # -- Audio capture --
    audio_capture = None
    try:
        from spotifycontroller.mixxx.audio_capture import AudioCapture, find_loopback_device

        if find_loopback_device() is not None:
            audio_capture = AudioCapture()
            print("Audio capture: AVAILABLE (use 'capture start' to begin)")
        else:
            print("Audio capture: no loopback device found")
    except Exception:
        _LOGGER.debug("Audio capture init failed", exc_info=True)

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
        print("No MIDI ports found — console-only mode.")

    # -- Console UI --
    run_console(
        mixer,
        playback,
        listener,
        audio_engine=audio_engine,
        audio_capture=audio_capture,
        mixxx_proc=mixxx_proc,
    )


if __name__ == "__main__":
    main()
