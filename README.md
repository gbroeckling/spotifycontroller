# SpotifyController (prototype)

SpotifyController is a **Windows DJ controller bridge for Spotify** — it maps MIDI hardware controls to Spotify playback, turning a physical DJ controller into a Spotify mixing surface.

This repository is a **prototype** built initially for the **Vestax VCI-380**, designed to support additional controllers down the road.

## What's in this repo (v0.0.1)
### Included now (working)
- MIDI listener with auto-detection of connected controllers
- Vestax VCI-380 full mapping (transport, jog, faders, EQ, hot-cues, loops, effects)
- Spotify OAuth authentication (browser-based, token cached locally)
- Two virtual decks (A/B) with independent track loading and state
- Crossfader + per-deck volume fader → Spotify volume control
- Jog wheel → track seeking (nudge forward/backward)
- Hot-cue pads → set and jump to cue points within a track
- Console UI with manual commands (search, load, play, devices, etc.)
- Pluggable controller architecture — add new hardware by subclassing `ControllerBase`

### Not yet implemented
- Beat sync / BPM detection (Spotify audio features API planned)
- Loop in/out (Spotify has no native loop support)
- Per-band EQ (values are tracked but Spotify has no EQ API)
- GUI (console-only for now)

### Documentation & roadmap
- Full product synopsis + plans: **docs/PROJECT_SYNOPSIS.md**

## Install (Windows)
1) **Python 3.12+** required. Install from [python.org](https://www.python.org/downloads/).
2) **Create a Spotify app** at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard):
   - Set redirect URI to `http://localhost:8888/callback`
   - Note your Client ID and Client Secret
3) Install dependencies:
   ```
   pip install -e .
   ```
4) Set your Spotify credentials:
   ```
   set SPOTIPY_CLIENT_ID=your_client_id_here
   set SPOTIPY_CLIENT_SECRET=your_client_secret_here
   ```
5) Connect your Vestax VCI-380 via USB.
6) Run:
   ```
   spotifycontroller
   ```

> Tip: Use `spotifycontroller --list-midi` to see available MIDI ports. Use `--midi-port "Port Name"` to select a specific port.

> Tip: Make sure Spotify is open and playing on a Spotify Connect device before starting.

## Adding a new controller
1) Create a new file in `spotifycontroller/midi/` (e.g., `pioneer_ddj400.py`)
2) Subclass `ControllerBase` and implement `build_mapping()` with your controller's MIDI CC/note map
3) Update `app.py` to select the controller (or add CLI flag for controller selection)

## Notes
- This prototype controls Spotify via the Web API — it requires an internet connection and an active Spotify Premium account.
- Spotify only supports a single active playback stream, so the two-deck model uses virtual decks with track loading/cueing rather than true simultaneous playback.
- The crossfader and volume faders control the Spotify volume output based on which deck is active.

## License
Apache-2.0 (see LICENSE)
