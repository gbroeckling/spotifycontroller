# SpotifyController — Project Synopsis

**One-line summary:** Turn any MIDI DJ controller into a Spotify mixing surface on Windows.

## Core Philosophy

DJing with Spotify should feel like DJing with real decks. The physical hardware — jog wheels,
faders, knobs, pads — should map intuitively to Spotify playback controls. The software should
be invisible: plug in your controller, authenticate with Spotify, and start mixing.

## Architecture

```
┌─────────────────┐     MIDI      ┌─────────────────┐    Spotify API    ┌─────────┐
│  DJ Controller  │──────────────→│ SpotifyController│────────────────→ │ Spotify │
│  (Vestax VCI-380│               │                  │                  │ Connect │
│   or any MIDI)  │               │  ┌────────────┐  │                  │ Device  │
└─────────────────┘               │  │ Controller │  │                  └─────────┘
                                  │  │  Mapping   │  │
                                  │  └─────┬──────┘  │
                                  │        │         │
                                  │  ┌─────▼──────┐  │
                                  │  │   Mixer    │  │
                                  │  │ Deck A / B │  │
                                  │  └─────┬──────┘  │
                                  │        │         │
                                  │  ┌─────▼──────┐  │
                                  │  │  Spotify   │  │
                                  │  │  Playback  │  │
                                  │  └────────────┘  │
                                  └─────────────────┘
```

### Layers

1. **MIDI Layer** (`spotifycontroller/midi/`)
   - `base.py` — abstract `ControllerBase` class + `ControllerMapping` dataclass
   - `listener.py` — threaded MIDI input reader using `python-rtmidi` via `mido`
   - `vestax_vci380.py` — concrete mapping for the Vestax VCI-380
   - Adding a controller = one new file, one class, one method (`build_mapping`)

2. **Spotify Layer** (`spotifycontroller/spotify/`)
   - `auth.py` — OAuth via `spotipy` with local token cache
   - `playback.py` — thin wrapper exposing DJ-style operations (play, pause, seek, volume, queue, search)

3. **Engine Layer** (`spotifycontroller/engine/`)
   - `deck.py` — virtual deck with loaded track, volume, EQ state, cue points
   - `mixer.py` — binds controller events → deck state → Spotify API calls

4. **UI Layer** (`spotifycontroller/ui/`)
   - `console.py` — interactive terminal for status, search, manual control

## Controller Support Roadmap

| Controller | Status | Notes |
|---|---|---|
| Vestax VCI-380 | In progress | Initial target, 2-channel + effects |
| Pioneer DDJ-400 | Planned | Popular entry-level, similar layout |
| Numark Mixtrack | Planned | Budget option |
| Generic MIDI | Planned | Learn-mode for arbitrary controllers |

## Spotify API Capabilities & Limitations

### What works
- Play/pause/skip/previous
- Seek to position
- Volume control (single global)
- Queue management
- Track/playlist search
- Device selection (Spotify Connect)
- Track metadata (name, artist, album, artwork, duration)

### Current limitations
- **Single stream:** Spotify only plays one track at a time — no true dual-deck mixing
- **No EQ:** Spotify API has no per-band equalizer
- **No loops:** No native loop-in/loop-out support
- **No BPM sync:** Audio features API provides tempo data but no real-time beat sync
- **Latency:** Web API round-trip adds ~100-300ms to every control action

### Future possibilities
- Use Spotify's audio features (tempo, key) for automatic track matching
- Local audio processing for EQ/effects (would require Spotify desktop integration)
- Pre-cueing via a second Spotify Connect device

## MVP Feature List (v0.1)
- [x] Vestax VCI-380 MIDI mapping
- [x] Spotify OAuth + token caching
- [x] Two virtual decks with track loading
- [x] Play/pause, seek, volume via controller
- [x] Hot-cue pads (set + recall)
- [x] Crossfader → volume blending
- [x] Console UI with search + status
- [ ] Controller auto-detection improvements
- [ ] Playlist browsing via browse encoder

## Pro Feature List (v1.0+)
- [ ] GUI with deck visualization and waveforms
- [ ] BPM detection + beat grid display
- [ ] Auto-mix / crossfade transitions
- [ ] MIDI learn mode for arbitrary controllers
- [ ] Multiple Spotify Connect device routing (deck A → device 1, deck B → device 2)
- [ ] Setlist / crate management
- [ ] Recording session history

## Testing Plan
- Unit tests for MIDI mapping lookups
- Unit tests for deck state management
- Integration tests with mocked Spotify client
- Manual testing with physical controller
