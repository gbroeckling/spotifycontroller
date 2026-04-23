"""DJ mixer — binds MIDI controller events to Spotify playback via virtual decks.

The mixer owns two virtual decks and a crossfader. It registers callbacks
on the controller driver so that physical knob/button actions translate
into Spotify API calls.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from spotifycontroller.const import (
    DECK_A,
    DECK_B,
    MAP_CROSSFADER,
    MAP_CUE,
    MAP_EQ_HI,
    MAP_EQ_LO,
    MAP_EQ_MID,
    MAP_HOTCUE_1,
    MAP_HOTCUE_2,
    MAP_HOTCUE_3,
    MAP_HOTCUE_4,
    MAP_JOG,
    MAP_LOAD,
    MAP_LOOP_IN,
    MAP_LOOP_OUT,
    MAP_PLAY,
    MAP_SYNC,
    MAP_VOLUME,
)
from spotifycontroller.engine.deck import Deck

if TYPE_CHECKING:
    from spotifycontroller.midi.base import ControllerBase, MidiControl
    from spotifycontroller.spotify.playback import SpotifyPlayback

_LOGGER = logging.getLogger(__name__)

# Jog-wheel nudge amount in milliseconds per MIDI tick
_JOG_NUDGE_MS = 500


class Mixer:
    """Two-deck mixer bridging a MIDI controller to Spotify."""

    def __init__(self, controller: ControllerBase, playback: SpotifyPlayback) -> None:
        self._controller = controller
        self._playback = playback
        self.deck_a = Deck(name=DECK_A)
        self.deck_b = Deck(name=DECK_B)
        self.crossfader: int = 64  # center
        self._active_deck: str = DECK_A
        self._browse_tracks: list[dict] = []
        self._browse_index: int = 0

    @property
    def active_deck(self) -> Deck:
        return self.deck_a if self._active_deck == DECK_A else self.deck_b

    def get_deck(self, deck_id: str) -> Deck:
        return self.deck_a if deck_id == DECK_A else self.deck_b

    # -- Setup --

    def bind(self) -> None:
        """Register all controller callbacks."""
        for deck_id in (DECK_A, DECK_B):
            prefix = f"deck_{deck_id.lower()}_"
            self._controller.on(prefix + MAP_PLAY, self._on_play)
            self._controller.on(prefix + MAP_CUE, self._on_cue)
            self._controller.on(prefix + MAP_SYNC, self._on_sync)
            self._controller.on(prefix + MAP_LOAD, self._on_load)
            self._controller.on(prefix + MAP_JOG, self._on_jog)
            self._controller.on(prefix + MAP_VOLUME, self._on_volume)
            self._controller.on(prefix + MAP_EQ_HI, self._on_eq)
            self._controller.on(prefix + MAP_EQ_MID, self._on_eq)
            self._controller.on(prefix + MAP_EQ_LO, self._on_eq)

            for hc in (MAP_HOTCUE_1, MAP_HOTCUE_2, MAP_HOTCUE_3, MAP_HOTCUE_4):
                self._controller.on(prefix + hc, self._on_hotcue)

            self._controller.on(prefix + MAP_LOOP_IN, self._on_loop)
            self._controller.on(prefix + MAP_LOOP_OUT, self._on_loop)

        self._controller.on(MAP_CROSSFADER, self._on_crossfader)
        _LOGGER.info("Mixer bound to controller: %s", self._controller.mapping.name)

    # -- Callbacks --

    def _on_play(self, control: MidiControl, value: int) -> None:
        if control.deck is None:
            return
        deck = self.get_deck(control.deck)
        if not deck.is_loaded:
            _LOGGER.warning("Deck %s: no track loaded", deck.name)
            return

        if deck.is_playing:
            self._playback.pause()
            deck.is_playing = False
            _LOGGER.info("Deck %s: paused", deck.name)
        else:
            self._playback.play(uri=deck.track.uri if deck.track else None)
            deck.is_playing = True
            self._active_deck = control.deck
            _LOGGER.info("Deck %s: playing", deck.name)

    def _on_cue(self, control: MidiControl, value: int) -> None:
        if control.deck is None:
            return
        deck = self.get_deck(control.deck)
        if deck.is_loaded:
            self._playback.seek(0)
            _LOGGER.info("Deck %s: cue — returned to start", deck.name)

    def _on_sync(self, control: MidiControl, value: int) -> None:
        # Spotify doesn't expose BPM sync — this is a placeholder for future
        # beat-matching features (e.g., tempo analysis via audio features API).
        if control.deck:
            _LOGGER.info("Deck %s: sync pressed (not yet implemented)", control.deck)

    def _on_load(self, control: MidiControl, value: int) -> None:
        if control.deck is None:
            return
        deck = self.get_deck(control.deck)
        # Load whatever is currently playing in Spotify onto this deck
        current = self._playback.get_current_track()
        if current:
            deck.load_track(current)
        else:
            _LOGGER.warning("Deck %s: nothing playing in Spotify to load", deck.name)

    def _on_jog(self, control: MidiControl, value: int) -> None:
        if control.deck is None:
            return
        # MIDI value 0-63 = backward, 65-127 = forward, 64 = center
        delta = (value - 64) * _JOG_NUDGE_MS
        if delta != 0:
            self._playback.nudge(delta)

    def _on_volume(self, control: MidiControl, value: int) -> None:
        if control.deck is None:
            return
        deck = self.get_deck(control.deck)
        deck.volume = value
        # Apply volume based on crossfader position
        self._apply_volumes()

    def _on_eq(self, control: MidiControl, value: int) -> None:
        if control.deck is None:
            return
        deck = self.get_deck(control.deck)
        if control.name.endswith(MAP_EQ_HI):
            deck.eq_hi = value
        elif control.name.endswith(MAP_EQ_MID):
            deck.eq_mid = value
        elif control.name.endswith(MAP_EQ_LO):
            deck.eq_lo = value
        # Spotify doesn't have per-band EQ — stored for future audio processing
        _LOGGER.debug("Deck %s: EQ hi=%d mid=%d lo=%d", deck.name, deck.eq_hi, deck.eq_mid, deck.eq_lo)

    def _on_hotcue(self, control: MidiControl, value: int) -> None:
        if control.deck is None:
            return
        deck = self.get_deck(control.deck)
        # Determine which pad number from control name
        for i, hc in enumerate((MAP_HOTCUE_1, MAP_HOTCUE_2, MAP_HOTCUE_3, MAP_HOTCUE_4), 1):
            if control.name.endswith(hc):
                if i in deck.cue_points:
                    self._playback.seek(deck.cue_points[i])
                    _LOGGER.info("Deck %s: jump to cue %d at %d ms", deck.name, i, deck.cue_points[i])
                else:
                    state = self._playback.get_state()
                    if state and state.get("progress_ms") is not None:
                        deck.set_cue_point(i, state["progress_ms"])
                break

    def _on_loop(self, control: MidiControl, value: int) -> None:
        # Spotify doesn't support native loop points — placeholder
        if control.deck:
            _LOGGER.info("Deck %s: loop %s (not yet implemented)", control.deck, control.name.split("_")[-1])

    def _on_crossfader(self, control: MidiControl, value: int) -> None:
        self.crossfader = value
        self._apply_volumes()

    def _apply_volumes(self) -> None:
        """Compute effective volume from deck faders + crossfader and send to Spotify.

        Since Spotify has a single volume control, we blend based on
        which deck is active and the crossfader position.
        """
        # Crossfader: 0 = full deck A, 127 = full deck B, 64 = center
        cf = self.crossfader / 127.0
        vol_a = self.deck_a.volume_percent() * (1.0 - cf)
        vol_b = self.deck_b.volume_percent() * cf

        # Active deck determines which volume is sent to Spotify
        if self._active_deck == DECK_A:
            effective = int(vol_a)
        else:
            effective = int(vol_b)

        effective = max(0, min(100, effective))
        try:
            self._playback.set_volume(effective)
        except Exception:
            _LOGGER.debug("Could not set volume (no active device?)")
