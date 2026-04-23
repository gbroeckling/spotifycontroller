"""MIDI input listener — reads from a MIDI port and dispatches to a controller driver."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

import mido

if TYPE_CHECKING:
    from spotifycontroller.midi.base import ControllerBase

_LOGGER = logging.getLogger(__name__)


def list_midi_ports() -> list[str]:
    """Return available MIDI input port names."""
    return mido.get_input_names()  # type: ignore[no-any-return]


class MidiListener:
    """Threaded MIDI listener that dispatches messages to a controller."""

    def __init__(self, controller: ControllerBase, port_name: str | None = None) -> None:
        self._controller = controller
        self._port_name = port_name
        self._port: mido.ports.BaseInput | None = None  # type: ignore[name-defined]
        self._thread: threading.Thread | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Open the MIDI port and start listening."""
        if self._running:
            return

        available = list_midi_ports()
        if not available:
            _LOGGER.error("No MIDI input ports found")
            return

        port_name = self._port_name
        if port_name is None:
            # Auto-detect: prefer a port whose name contains the controller name
            controller_name = self._controller.mapping.name.lower()
            for name in available:
                if controller_name in name.lower() or "vestax" in name.lower():
                    port_name = name
                    break
            if port_name is None:
                port_name = available[0]
                _LOGGER.warning("Controller not found, defaulting to '%s'", port_name)

        _LOGGER.info("Opening MIDI port: %s", port_name)
        self._port = mido.open_input(port_name)  # type: ignore[assignment]
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="midi-listener")
        self._thread.start()

    def stop(self) -> None:
        """Stop listening and close the port."""
        self._running = False
        if self._port is not None:
            self._port.close()
            self._port = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def _run(self) -> None:
        """Read loop — runs in a background thread."""
        mapping = self._controller.mapping
        assert self._port is not None  # noqa: S101

        _LOGGER.info("MIDI listener started on '%s'", self._port.name)
        while self._running:
            try:
                for msg in self._port.iter_pending():
                    self._handle_message(msg, mapping)
            except Exception:
                if self._running:
                    _LOGGER.exception("Error reading MIDI")
                break

            # Yield to avoid busy-waiting — iter_pending is non-blocking
            threading.Event().wait(0.005)

    def _handle_message(self, msg: mido.Message, mapping: object) -> None:
        """Translate a raw MIDI message into a controller dispatch."""
        from spotifycontroller.midi.base import ControllerMapping

        assert isinstance(mapping, ControllerMapping)  # noqa: S101

        if msg.type in ("note_on", "note_off"):
            msg_type = "note_on" if msg.type == "note_on" and msg.velocity > 0 else "note_off"
            control = mapping.get_control_by_midi(msg_type, msg.channel, msg.note)
            if control is not None:
                self._controller.dispatch(control, msg.velocity)
            else:
                _LOGGER.debug("Unmapped: %s ch=%d note=%d vel=%d", msg.type, msg.channel, msg.note, msg.velocity)

        elif msg.type == "control_change":
            control = mapping.get_control_by_midi("control_change", msg.channel, msg.control)
            if control is not None:
                self._controller.dispatch(control, msg.value)
            else:
                _LOGGER.debug("Unmapped: CC ch=%d cc=%d val=%d", msg.channel, msg.control, msg.value)
