"""WASAPI audio capture — routes system audio into Mixxx or the local audio engine.

Uses Windows WASAPI loopback to capture audio from any application (e.g., Spotify)
and feeds it in real-time to a virtual audio output. This is the same mechanism
OBS Studio, Discord, and Zoom use for application audio capture.

The captured audio is processed in real-time (never saved to disk) and can be:
  - Routed to a virtual audio cable for Mixxx to pick up as a live input
  - Fed directly to our local audio engine for mixing

Requirements:
  - Windows 10+ (WASAPI loopback support)
  - pip install sounddevice numpy
  - Optional: VB-Cable or similar virtual audio device for routing to Mixxx
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable

_LOGGER = logging.getLogger(__name__)

try:
    import sounddevice as sd

    _SD_AVAILABLE = True
except ImportError:
    _SD_AVAILABLE = False


def list_audio_devices() -> list[dict]:
    """Return all available audio devices with their properties."""
    if not _SD_AVAILABLE:
        return []
    devices = sd.query_devices()
    result = []
    for i, dev in enumerate(devices):
        result.append({
            "index": i,
            "name": dev["name"],
            "max_input_channels": dev["max_input_channels"],
            "max_output_channels": dev["max_output_channels"],
            "default_samplerate": dev["default_samplerate"],
            "hostapi": sd.query_hostapis(dev["hostapi"])["name"],
        })
    return result


def find_loopback_device() -> int | None:
    """Find a WASAPI loopback device for capturing system audio.

    On Windows, WASAPI loopback devices let you capture the audio output
    of any application. They typically appear as input devices with
    "loopback" in the name or on the WASAPI host API.
    """
    if not _SD_AVAILABLE:
        return None

    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        hostapi = sd.query_hostapis(dev["hostapi"])["name"]
        name = dev["name"].lower()
        # Look for WASAPI loopback devices or Stereo Mix (Realtek exposes this)
        loopback_keywords = ["loopback", "stereo mix", "what u hear", "wave out"]
        if dev["max_input_channels"] > 0 and any(kw in name for kw in loopback_keywords):
            _LOGGER.info("Found loopback device: [%d] %s (%s)", i, dev["name"], hostapi)
            return i
        # On some systems, WASAPI output devices can be opened as loopback
        if "wasapi" in hostapi.lower() and "speakers" in name and dev["max_input_channels"] > 0:
            _LOGGER.info("Found WASAPI speakers (loopback capable): [%d] %s", i, dev["name"])
            return i

    return None


def find_virtual_cable_output() -> int | None:
    """Find a virtual audio cable output device (like VB-Cable) for routing audio to Mixxx."""
    if not _SD_AVAILABLE:
        return None

    devices = sd.query_devices()
    cable_keywords = ["cable", "virtual", "vb-audio", "voicemeeter"]
    for i, dev in enumerate(devices):
        name = dev["name"].lower()
        if dev["max_output_channels"] > 0 and any(kw in name for kw in cable_keywords):
            _LOGGER.info("Found virtual cable output: [%d] %s", i, dev["name"])
            return i

    return None


class AudioCapture:
    """Captures audio from a system loopback device and routes it.

    The captured audio is kept in a ring buffer and can be read by the
    audio engine or routed to a virtual cable for Mixxx.
    """

    def __init__(
        self,
        input_device: int | None = None,
        output_device: int | None = None,
        sample_rate: int = 44100,
        channels: int = 2,
        buffer_seconds: float = 5.0,
    ) -> None:
        self._input_device = input_device
        self._output_device = output_device
        self._sample_rate = sample_rate
        self._channels = channels
        self._buffer_size = int(sample_rate * buffer_seconds * channels)
        self._buffer = np.zeros(self._buffer_size, dtype=np.float32)
        self._write_pos = 0
        self._lock = threading.Lock()
        self._stream: sd.Stream | None = None  # type: ignore[name-defined]
        self._running = False
        self._callbacks: list[Callable[[np.ndarray], None]] = []

    @property
    def is_running(self) -> bool:
        return self._running

    def on_audio(self, callback: Callable[[np.ndarray], None]) -> None:
        """Register a callback that receives audio buffers in real-time."""
        self._callbacks.append(callback)

    def start(self) -> bool:
        """Start capturing audio."""
        if not _SD_AVAILABLE:
            _LOGGER.error("sounddevice not installed")
            return False

        if self._running:
            return True

        input_dev = self._input_device or find_loopback_device()
        if input_dev is None:
            _LOGGER.error(
                "No loopback device found. On Windows, install a WASAPI-capable "
                "audio backend or use a virtual audio cable."
            )
            return False

        try:
            kwargs = {
                "samplerate": self._sample_rate,
                "channels": self._channels,
                "dtype": "float32",
                "callback": self._audio_callback,
                "blocksize": 1024,
            }

            if self._output_device is not None:
                # Full-duplex: capture from loopback, output to virtual cable
                self._stream = sd.Stream(
                    device=(input_dev, self._output_device),
                    **kwargs,
                )
            else:
                # Input only: capture and buffer for the audio engine
                self._stream = sd.InputStream(
                    device=input_dev,
                    **kwargs,
                )

            self._stream.start()
            self._running = True

            dev_info = sd.query_devices(input_dev)
            _LOGGER.info("Audio capture started from: %s", dev_info["name"])
            return True

        except Exception:
            _LOGGER.exception("Failed to start audio capture")
            return False

    def stop(self) -> None:
        """Stop capturing."""
        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            _LOGGER.info("Audio capture stopped")

    def _audio_callback(
        self,
        indata: np.ndarray,
        outdata: np.ndarray | None,
        frames: int,
        time_info: object,
        status: object,
    ) -> None:
        """Process captured audio — buffer it and notify callbacks."""
        if status:
            _LOGGER.debug("Capture status: %s", status)

        # Store in ring buffer
        flat = indata.flatten()
        n = len(flat)
        with self._lock:
            end = self._write_pos + n
            if end <= self._buffer_size:
                self._buffer[self._write_pos:end] = flat
            else:
                first = self._buffer_size - self._write_pos
                self._buffer[self._write_pos:] = flat[:first]
                self._buffer[:n - first] = flat[first:]
            self._write_pos = end % self._buffer_size

        # Pass-through to output (if full-duplex for virtual cable routing)
        if outdata is not None:
            outdata[:] = indata

        # Notify callbacks
        for cb in self._callbacks:
            try:
                cb(indata.copy())
            except Exception:
                _LOGGER.debug("Audio callback error", exc_info=True)

    def get_recent_audio(self, seconds: float = 1.0) -> np.ndarray:
        """Get the most recent N seconds of captured audio from the ring buffer."""
        n_samples = int(seconds * self._sample_rate * self._channels)
        n_samples = min(n_samples, self._buffer_size)

        with self._lock:
            end = self._write_pos
            start = (end - n_samples) % self._buffer_size
            if start < end:
                return self._buffer[start:end].copy()
            else:
                return np.concatenate([
                    self._buffer[start:],
                    self._buffer[:end],
                ]).copy()


def print_audio_routing_status() -> None:
    """Print status of audio devices and routing options."""
    if not _SD_AVAILABLE:
        print("  sounddevice not installed — pip install sounddevice")
        return

    print("\n=== Audio Routing Status ===")

    loopback = find_loopback_device()
    if loopback is not None:
        dev = sd.query_devices(loopback)
        print(f"  Loopback device: [{loopback}] {dev['name']}")
    else:
        print("  Loopback device: NOT FOUND")
        print("  Tip: Some WASAPI drivers expose loopback devices.")
        print("       You may need to enable 'Stereo Mix' in Windows Sound settings.")

    cable = find_virtual_cable_output()
    if cable is not None:
        dev = sd.query_devices(cable)
        print(f"  Virtual cable:   [{cable}] {dev['name']}")
    else:
        print("  Virtual cable:   NOT FOUND")
        print("  Tip: Install VB-Cable (free) from https://vb-audio.com/Cable/")
        print("       This lets Spotify audio flow directly into Mixxx.")

    print("\n  All audio devices:")
    for dev in list_audio_devices():
        direction = ""
        if dev["max_input_channels"] > 0 and dev["max_output_channels"] > 0:
            direction = "IN/OUT"
        elif dev["max_input_channels"] > 0:
            direction = "IN"
        elif dev["max_output_channels"] > 0:
            direction = "OUT"
        print(f"    [{dev['index']:2d}] {dev['name']:<40} {direction:<6} ({dev['hostapi']})")

    print("============================\n")
