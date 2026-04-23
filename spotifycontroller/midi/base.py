"""Abstract base class for DJ controller MIDI mappings."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class MidiControl:
    """A single MIDI control point on a controller."""

    name: str
    message_type: str  # "note_on", "control_change"
    channel: int
    note_or_cc: int
    deck: str | None = None  # "A", "B", or None for global


@dataclass
class ControllerMapping:
    """Complete MIDI mapping for a DJ controller."""

    name: str
    vendor: str
    controls: dict[str, MidiControl] = field(default_factory=dict)

    def get_control_by_midi(self, msg_type: str, channel: int, note_or_cc: int) -> MidiControl | None:
        """Look up a control from raw MIDI data."""
        for control in self.controls.values():
            if (
                control.message_type == msg_type
                and control.channel == channel
                and control.note_or_cc == note_or_cc
            ):
                return control
        return None


class ControllerBase(ABC):
    """Abstract base for a DJ controller driver.

    Subclass this to add support for a new controller. Implement
    ``build_mapping`` to define the MIDI CC/note map for your hardware,
    then register it with the listener.
    """

    def __init__(self) -> None:
        self._mapping: ControllerMapping | None = None
        self._callbacks: dict[str, list[Callable]] = {}

    @property
    def mapping(self) -> ControllerMapping:
        if self._mapping is None:
            self._mapping = self.build_mapping()
        return self._mapping

    @abstractmethod
    def build_mapping(self) -> ControllerMapping:
        """Return the MIDI mapping for this controller."""

    def on(self, control_name: str, callback: Callable) -> None:
        """Register a callback for a named control."""
        self._callbacks.setdefault(control_name, []).append(callback)

    def dispatch(self, control: MidiControl, value: int) -> None:
        """Dispatch a MIDI event to registered callbacks."""
        key = control.name
        for cb in self._callbacks.get(key, []):
            try:
                cb(control, value)
            except Exception:
                _LOGGER.exception("Error in callback for %s", key)
