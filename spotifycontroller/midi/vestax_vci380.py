"""Vestax VCI-380 MIDI mapping.

The VCI-380 is a 2-channel DJ controller with jogwheels, channel faders,
crossfader, 3-band EQ per channel, transport controls, hot-cue pads,
loop controls, and an effects section.

MIDI note/CC values below are based on the VCI-380's native MIDI mode.
Adjust if your unit runs custom firmware or a different MIDI channel.
"""

from __future__ import annotations

from spotifycontroller.const import (
    DECK_A,
    DECK_B,
    MAP_BROWSE,
    MAP_CROSSFADER,
    MAP_CUE,
    MAP_EQ_HI,
    MAP_EQ_LO,
    MAP_EQ_MID,
    MAP_FX1,
    MAP_FX2,
    MAP_FX3,
    MAP_HOTCUE_1,
    MAP_HOTCUE_2,
    MAP_HOTCUE_3,
    MAP_HOTCUE_4,
    MAP_JOG,
    MAP_LOAD,
    MAP_LOOP_IN,
    MAP_LOOP_OUT,
    MAP_PITCH,
    MAP_PLAY,
    MAP_SYNC,
    MAP_VOLUME,
)
from spotifycontroller.midi.base import ControllerBase, ControllerMapping, MidiControl

# -- Channel assignments --
# Deck A lives on MIDI channel 0, Deck B on channel 1,
# global controls (crossfader, browse) on channel 2.
_CH_DECK_A = 0
_CH_DECK_B = 1
_CH_GLOBAL = 2


def _deck_controls(deck: str, ch: int) -> dict[str, MidiControl]:
    """Build the per-deck control map."""
    prefix = f"deck_{deck.lower()}_"
    return {
        # Transport buttons (note_on)
        prefix + MAP_PLAY: MidiControl(
            name=prefix + MAP_PLAY, message_type="note_on", channel=ch, note_or_cc=0x01, deck=deck
        ),
        prefix + MAP_CUE: MidiControl(
            name=prefix + MAP_CUE, message_type="note_on", channel=ch, note_or_cc=0x02, deck=deck
        ),
        prefix + MAP_SYNC: MidiControl(
            name=prefix + MAP_SYNC, message_type="note_on", channel=ch, note_or_cc=0x03, deck=deck
        ),
        # Load track onto this deck
        prefix + MAP_LOAD: MidiControl(
            name=prefix + MAP_LOAD, message_type="note_on", channel=ch, note_or_cc=0x04, deck=deck
        ),
        # Hot-cue pads (note_on)
        prefix + MAP_HOTCUE_1: MidiControl(
            name=prefix + MAP_HOTCUE_1, message_type="note_on", channel=ch, note_or_cc=0x10, deck=deck
        ),
        prefix + MAP_HOTCUE_2: MidiControl(
            name=prefix + MAP_HOTCUE_2, message_type="note_on", channel=ch, note_or_cc=0x11, deck=deck
        ),
        prefix + MAP_HOTCUE_3: MidiControl(
            name=prefix + MAP_HOTCUE_3, message_type="note_on", channel=ch, note_or_cc=0x12, deck=deck
        ),
        prefix + MAP_HOTCUE_4: MidiControl(
            name=prefix + MAP_HOTCUE_4, message_type="note_on", channel=ch, note_or_cc=0x13, deck=deck
        ),
        # Loop controls
        prefix + MAP_LOOP_IN: MidiControl(
            name=prefix + MAP_LOOP_IN, message_type="note_on", channel=ch, note_or_cc=0x20, deck=deck
        ),
        prefix + MAP_LOOP_OUT: MidiControl(
            name=prefix + MAP_LOOP_OUT, message_type="note_on", channel=ch, note_or_cc=0x21, deck=deck
        ),
        # Effects (note_on)
        prefix + MAP_FX1: MidiControl(
            name=prefix + MAP_FX1, message_type="note_on", channel=ch, note_or_cc=0x30, deck=deck
        ),
        prefix + MAP_FX2: MidiControl(
            name=prefix + MAP_FX2, message_type="note_on", channel=ch, note_or_cc=0x31, deck=deck
        ),
        prefix + MAP_FX3: MidiControl(
            name=prefix + MAP_FX3, message_type="note_on", channel=ch, note_or_cc=0x32, deck=deck
        ),
        # Continuous controls (control_change)
        prefix + MAP_JOG: MidiControl(
            name=prefix + MAP_JOG, message_type="control_change", channel=ch, note_or_cc=0x40, deck=deck
        ),
        prefix + MAP_PITCH: MidiControl(
            name=prefix + MAP_PITCH, message_type="control_change", channel=ch, note_or_cc=0x41, deck=deck
        ),
        prefix + MAP_VOLUME: MidiControl(
            name=prefix + MAP_VOLUME, message_type="control_change", channel=ch, note_or_cc=0x42, deck=deck
        ),
        prefix + MAP_EQ_HI: MidiControl(
            name=prefix + MAP_EQ_HI, message_type="control_change", channel=ch, note_or_cc=0x43, deck=deck
        ),
        prefix + MAP_EQ_MID: MidiControl(
            name=prefix + MAP_EQ_MID, message_type="control_change", channel=ch, note_or_cc=0x44, deck=deck
        ),
        prefix + MAP_EQ_LO: MidiControl(
            name=prefix + MAP_EQ_LO, message_type="control_change", channel=ch, note_or_cc=0x45, deck=deck
        ),
    }


class VestaxVCI380(ControllerBase):
    """Vestax VCI-380 DJ controller driver."""

    def build_mapping(self) -> ControllerMapping:
        controls: dict[str, MidiControl] = {}

        # Per-deck controls
        controls.update(_deck_controls(DECK_A, _CH_DECK_A))
        controls.update(_deck_controls(DECK_B, _CH_DECK_B))

        # Global controls
        controls[MAP_CROSSFADER] = MidiControl(
            name=MAP_CROSSFADER, message_type="control_change", channel=_CH_GLOBAL, note_or_cc=0x01
        )
        controls[MAP_BROWSE] = MidiControl(
            name=MAP_BROWSE, message_type="control_change", channel=_CH_GLOBAL, note_or_cc=0x02
        )

        return ControllerMapping(name="Vestax VCI-380", vendor="Vestax", controls=controls)
