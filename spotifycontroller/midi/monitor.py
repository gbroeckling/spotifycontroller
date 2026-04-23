"""MIDI monitor — prints every incoming MIDI message raw.

Run with ``spotifycontroller --midi-monitor`` to see exactly what your
controller sends. Press each button, turn each knob, and note the
channel / note / CC numbers. Use these values to correct or build
a controller mapping.
"""

from __future__ import annotations

import sys

import mido

from spotifycontroller.midi.listener import list_midi_ports


def run_monitor(port_name: str | None = None) -> None:
    """Open a MIDI port and print every message until Ctrl-C."""
    available = list_midi_ports()
    if not available:
        print("No MIDI input ports found.")
        sys.exit(1)

    if port_name is None:
        print("Available MIDI input ports:")
        for i, name in enumerate(available, 1):
            print(f"  {i}. {name}")
        print()
        choice = input("Select port number (or Enter for first): ").strip()
        if choice:
            try:
                port_name = available[int(choice) - 1]
            except (ValueError, IndexError):
                print("Invalid selection.")
                sys.exit(1)
        else:
            port_name = available[0]

    print(f"\nOpening: {port_name}")
    print("Press buttons, turn knobs, move faders on your controller.")
    print("Each MIDI message will be printed below. Ctrl-C to stop.\n")
    print(f"{'Type':<18} {'Channel':<10} {'Note/CC':<12} {'Value':<8} {'Hex'}")
    print("-" * 70)

    port = mido.open_input(port_name)
    try:
        for msg in port:
            if msg.type == "note_on":
                print(
                    f"{'NOTE ON':<18} {msg.channel + 1:<10} {msg.note:<12} "
                    f"{msg.velocity:<8} ch={msg.channel:#04x} note={msg.note:#04x} vel={msg.velocity:#04x}"
                )
            elif msg.type == "note_off":
                print(
                    f"{'NOTE OFF':<18} {msg.channel + 1:<10} {msg.note:<12} "
                    f"{msg.velocity:<8} ch={msg.channel:#04x} note={msg.note:#04x} vel={msg.velocity:#04x}"
                )
            elif msg.type == "control_change":
                print(
                    f"{'CC':<18} {msg.channel + 1:<10} {msg.control:<12} "
                    f"{msg.value:<8} ch={msg.channel:#04x} cc={msg.control:#04x} val={msg.value:#04x}"
                )
            elif msg.type == "pitchwheel":
                print(
                    f"{'PITCH BEND':<18} {msg.channel + 1:<10} {'—':<12} "
                    f"{msg.pitch:<8} ch={msg.channel:#04x} pitch={msg.pitch}"
                )
            else:
                print(f"{msg.type:<18} {msg}")
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
    finally:
        port.close()
