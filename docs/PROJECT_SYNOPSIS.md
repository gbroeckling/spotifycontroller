# SpotifyController — Project Synopsis

**One-line summary:** Turn any MIDI DJ controller into a Spotify mixing surface on Windows, with a local audio engine for real dual-deck DJ'ing.

## Core Philosophy

DJing with Spotify should feel like DJing with real decks. The physical hardware — jog wheels,
faders, knobs, pads — should map intuitively to playback controls. The software should
be invisible: plug in your controller, authenticate with Spotify, and start mixing.

For full DJ capability (true dual-deck, EQ, effects), the local audio engine plays your own
music files with sub-millisecond latency while Spotify handles discovery and browsing.

## Architecture

```
┌───────────────┐                    ┌─────────────────────────────┐
│ Spotify API   │ search/browse/     │     SpotifyController       │
│ (Web API)     │────metadata───────→│                             │
└───────────────┘                    │  ┌───────────────────────┐  │
                                     │  │  Spotify Playback     │  │
                                     │  │  (play/pause/seek/    │  │
                                     │  │   vol/next/prev)      │  │
                                     │  └───────────┬───────────┘  │
┌───────────────┐  load local file   │  ┌───────────▼───────────┐  │      ┌──────────┐
│ Local files   │───────────────────→│  │   Audio Engine        │  │      │          │
│ (MP3/FLAC/WAV)│                    │  │  Deck A ──┐           │  │      │ Speakers │
└───────────────┘                    │  │  Deck B ──┼→ mixer ───┼──┼─────→│          │
                                     │  │  EQ/FX ───┘           │  │      └──────────┘
┌───────────────┐      MIDI          │  └───────────────────────┘  │
│  VCI-380      │───────────────────→│                             │
│  (or any      │                    │  ┌───────────────────────┐  │
│   controller) │                    │  │  Mixer (binds MIDI    │  │
└───────────────┘                    │  │   → decks → playback) │  │
                                     │  └───────────────────────┘  │
                                     └─────────────────────────────┘
```

### Layers

1. **MIDI Layer** (`spotifycontroller/midi/`)
   - `base.py` — abstract `ControllerBase` class + `ControllerMapping` dataclass
   - `listener.py` — threaded MIDI input reader using `python-rtmidi` via `mido`
   - `monitor.py` — raw MIDI message printer for mapping verification
   - `vestax_vci380.py` — concrete mapping for the Vestax VCI-380
   - Adding a controller = one new file, one class, one method (`build_mapping`)

2. **Spotify Layer** (`spotifycontroller/spotify/`)
   - `auth.py` — OAuth via `spotipy` with local token cache
   - `playback.py` — thin wrapper exposing DJ-style operations (play, pause, seek, volume, queue, search)

3. **Engine Layer** (`spotifycontroller/engine/`)
   - `deck.py` — virtual deck with loaded track, volume, EQ state, cue points (Spotify mode)
   - `mixer.py` — binds controller events → deck state → Spotify API calls
   - `audio.py` — local audio engine with real dual-deck playback, crossfader mixing, and EQ

4. **UI Layer** (`spotifycontroller/ui/`)
   - `console.py` — interactive terminal for status, search, manual control, audio commands

## Two Playback Modes

### Spotify API Mode (default)
- Controls Spotify via Web API (remote control)
- Single playback stream, virtual dual-deck
- Great for: casual mixing, playlist browsing, track discovery
- Limitation: ~100-300ms latency, no real EQ/effects

### Local Audio Mode (with `[audio]` extras)
- Loads local music files (MP3, FLAC, WAV) onto real audio decks
- True dual-deck simultaneous playback via sounddevice
- Real crossfader mixing, volume per-deck
- Foundation for: real-time EQ, effects, beat sync
- Great for: real DJ sets with music you own

Both modes work together — browse and discover on Spotify, then load your
own files for the actual set.

## Controller Support Roadmap

| Controller | Status | Notes |
|---|---|---|
| Vestax VCI-380 | In progress | Initial target, 2-channel + effects |
| Pioneer DDJ-400 | Planned | Popular entry-level, similar layout |
| Numark Mixtrack | Planned | Budget option |
| Generic MIDI | Planned | Learn-mode for arbitrary controllers |

## VCI-380 MIDI Mapping Sources

Vestax went bankrupt in 2014 and official documentation is offline. Our mapping is built from:
- **Confirmed** VCI-380 data from Serato forum posts and PowerOnPlay SSL mapping
- **Inferred** from VCI-400 Mixxx mapping (sister controller, same architecture)
- **Community** Traktor mapping by Georg Ziegler (v3.4)

Use `--midi-monitor` to verify every control against your actual hardware.

Key findings:
- Deck A = MIDI channel 8 (zero-indexed: 7)
- Deck B = MIDI channel 9 (zero-indexed: 8)
- Hot-cue pads confirmed at notes 60-63 (0x3C-0x3F)
- Jog wheel touch = note 26 (0x1A), rotation = CC 19 (0x13)
- Transport buttons inferred from VCI-400: Play=0x1A, Cue=0x19, Sync=0x01

## MVP Feature List (v0.1)
- [x] Vestax VCI-380 MIDI mapping (with real values from research)
- [x] MIDI monitor mode for mapping verification
- [x] Spotify OAuth + token caching
- [x] Two virtual decks with track loading
- [x] Play/pause works without pre-loading a track
- [x] Next/previous track navigation
- [x] Seek via jog wheel, volume via faders
- [x] Hot-cue pads (set + recall)
- [x] Crossfader → volume blending
- [x] Console UI with search + status + audio commands
- [x] Local audio engine (dual-deck, crossfader)
- [ ] Controller auto-detection improvements
- [ ] Playlist browsing via browse encoder

## Pro Feature List (v1.0+)
- [ ] Real-time 3-band EQ on local audio engine
- [ ] Audio effects (filter, delay, reverb)
- [ ] BPM detection + beat grid display
- [ ] Auto-mix / crossfade transitions
- [ ] GUI with deck visualization and waveforms
- [ ] MIDI learn mode for arbitrary controllers
- [ ] Multiple audio output routing (deck A → output 1, deck B → output 2)
- [ ] Headphone pre-listen (PFL/cue) on separate output
- [ ] Setlist / crate management
- [ ] Recording session history

## Testing Plan
- Unit tests for MIDI mapping lookups
- Unit tests for deck state management
- Unit tests for audio engine mixing math
- Integration tests with mocked Spotify client
- Manual testing with physical controller + MIDI monitor
