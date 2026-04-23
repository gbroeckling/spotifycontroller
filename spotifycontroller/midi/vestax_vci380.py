"""Vestax VCI-380 MIDI mapping.

The VCI-380 is a 2-channel DJ controller with jogwheels, channel faders,
crossfader, 3-band EQ per channel, transport controls, hot-cue pads,
loop controls, and an effects section.

MIDI values below are sourced from:
  - Confirmed VCI-380 data (Serato forum, PowerOnPlay SSL mapping)
  - VCI-400 Mixxx mapping (sister controller, same Vestax MIDI architecture)
  - Community Traktor mapping by Georg Ziegler (v3.4)

Since Vestax went bankrupt in 2014 and official docs are offline, some
values are inferred from the VCI-400. Run ``--midi-monitor`` to verify
every control against your actual hardware and adjust as needed.

Channel layout (confirmed):
  Deck A = MIDI channel 8 (zero-indexed: 7)
  Deck B = MIDI channel 9 (zero-indexed: 8)
  Global  = MIDI channel 1 (zero-indexed: 0)
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
    MAP_NEXT,
    MAP_PFL,
    MAP_PITCH,
    MAP_PLAY,
    MAP_PREV,
    MAP_SYNC,
    MAP_TRIM,
    MAP_VOLUME,
)
from spotifycontroller.midi.base import ControllerBase, ControllerMapping, MidiControl

# -- Channel assignments (zero-indexed) --
# Confirmed from Serato forum + PowerOnPlay + community mappings.
_CH_DECK_A = 7   # MIDI channel 8
_CH_DECK_B = 8   # MIDI channel 9
_CH_GLOBAL = 0   # MIDI channel 1


def _deck_controls(deck: str, ch: int) -> dict[str, MidiControl]:
    """Build the per-deck control map.

    Note/CC numbers sourced from VCI-400 Mixxx mapping (fhennig/GitHub)
    and confirmed VCI-380 community data where available.
    """
    prefix = f"deck_{deck.lower()}_"
    return {
        # -- Transport buttons (note_on) --
        # VCI-400: play=0x1A, cue=0x19, sync=0x01
        prefix + MAP_PLAY: MidiControl(
            name=prefix + MAP_PLAY, message_type="note_on", channel=ch, note_or_cc=0x1A, deck=deck
        ),
        prefix + MAP_CUE: MidiControl(
            name=prefix + MAP_CUE, message_type="note_on", channel=ch, note_or_cc=0x19, deck=deck
        ),
        prefix + MAP_SYNC: MidiControl(
            name=prefix + MAP_SYNC, message_type="note_on", channel=ch, note_or_cc=0x01, deck=deck
        ),
        # Load track onto this deck (VCI-400: 0x02)
        prefix + MAP_LOAD: MidiControl(
            name=prefix + MAP_LOAD, message_type="note_on", channel=ch, note_or_cc=0x02, deck=deck
        ),
        # PFL / headphone cue (VCI-400: 0x05)
        prefix + MAP_PFL: MidiControl(
            name=prefix + MAP_PFL, message_type="note_on", channel=ch, note_or_cc=0x05, deck=deck
        ),

        # -- Navigate: next/prev track --
        # Using VCI-380 forward/back buttons (0x03, 0x04 — adjacent to load)
        prefix + MAP_NEXT: MidiControl(
            name=prefix + MAP_NEXT, message_type="note_on", channel=ch, note_or_cc=0x03, deck=deck
        ),
        prefix + MAP_PREV: MidiControl(
            name=prefix + MAP_PREV, message_type="note_on", channel=ch, note_or_cc=0x04, deck=deck
        ),

        # -- Hot-cue pads (note_on) --
        # Confirmed VCI-380: pads start at note 60 (0x3C)
        prefix + MAP_HOTCUE_1: MidiControl(
            name=prefix + MAP_HOTCUE_1, message_type="note_on", channel=ch, note_or_cc=0x3C, deck=deck
        ),
        prefix + MAP_HOTCUE_2: MidiControl(
            name=prefix + MAP_HOTCUE_2, message_type="note_on", channel=ch, note_or_cc=0x3D, deck=deck
        ),
        prefix + MAP_HOTCUE_3: MidiControl(
            name=prefix + MAP_HOTCUE_3, message_type="note_on", channel=ch, note_or_cc=0x3E, deck=deck
        ),
        prefix + MAP_HOTCUE_4: MidiControl(
            name=prefix + MAP_HOTCUE_4, message_type="note_on", channel=ch, note_or_cc=0x3F, deck=deck
        ),

        # -- Loop controls (note_on) --
        prefix + MAP_LOOP_IN: MidiControl(
            name=prefix + MAP_LOOP_IN, message_type="note_on", channel=ch, note_or_cc=0x20, deck=deck
        ),
        prefix + MAP_LOOP_OUT: MidiControl(
            name=prefix + MAP_LOOP_OUT, message_type="note_on", channel=ch, note_or_cc=0x21, deck=deck
        ),

        # -- Effects (note_on) --
        prefix + MAP_FX1: MidiControl(
            name=prefix + MAP_FX1, message_type="note_on", channel=ch, note_or_cc=0x30, deck=deck
        ),
        prefix + MAP_FX2: MidiControl(
            name=prefix + MAP_FX2, message_type="note_on", channel=ch, note_or_cc=0x31, deck=deck
        ),
        prefix + MAP_FX3: MidiControl(
            name=prefix + MAP_FX3, message_type="note_on", channel=ch, note_or_cc=0x32, deck=deck
        ),

        # -- Continuous controls (control_change) --
        # Jog wheel rotation (VCI-400: CC 0x13 = 19)
        prefix + MAP_JOG: MidiControl(
            name=prefix + MAP_JOG, message_type="control_change", channel=ch, note_or_cc=0x13, deck=deck
        ),
        # Pitch/tempo fader (VCI-400: CC 0x12 = 18 coarse)
        prefix + MAP_PITCH: MidiControl(
            name=prefix + MAP_PITCH, message_type="control_change", channel=ch, note_or_cc=0x12, deck=deck
        ),
        # Channel volume fader (VCI-400: CC 0x11 = 17)
        prefix + MAP_VOLUME: MidiControl(
            name=prefix + MAP_VOLUME, message_type="control_change", channel=ch, note_or_cc=0x11, deck=deck
        ),
        # Trim/gain knob (VCI-400: CC 0x0C = 12)
        prefix + MAP_TRIM: MidiControl(
            name=prefix + MAP_TRIM, message_type="control_change", channel=ch, note_or_cc=0x0C, deck=deck
        ),
        # 3-band EQ (VCI-400: hi=0x0D, mid=0x0E, lo=0x0F)
        prefix + MAP_EQ_HI: MidiControl(
            name=prefix + MAP_EQ_HI, message_type="control_change", channel=ch, note_or_cc=0x0D, deck=deck
        ),
        prefix + MAP_EQ_MID: MidiControl(
            name=prefix + MAP_EQ_MID, message_type="control_change", channel=ch, note_or_cc=0x0E, deck=deck
        ),
        prefix + MAP_EQ_LO: MidiControl(
            name=prefix + MAP_EQ_LO, message_type="control_change", channel=ch, note_or_cc=0x0F, deck=deck
        ),
    }


class VestaxVCI380(ControllerBase):
    """Vestax VCI-380 DJ controller driver."""

    def build_mapping(self) -> ControllerMapping:
        controls: dict[str, MidiControl] = {}

        # Per-deck controls
        controls.update(_deck_controls(DECK_A, _CH_DECK_A))
        controls.update(_deck_controls(DECK_B, _CH_DECK_B))

        # Global controls (channel 1 / zero-indexed 0)
        # Crossfader (VCI-400: CC 0x14 = 20)
        controls[MAP_CROSSFADER] = MidiControl(
            name=MAP_CROSSFADER, message_type="control_change", channel=_CH_GLOBAL, note_or_cc=0x14
        )
        # Browse encoder rotation (VCI-400: CC 0x28 = 40 on ch 0x0E)
        controls[MAP_BROWSE] = MidiControl(
            name=MAP_BROWSE, message_type="control_change", channel=_CH_GLOBAL, note_or_cc=0x28
        )

        return ControllerMapping(name="Vestax VCI-380", vendor="Vestax", controls=controls)
