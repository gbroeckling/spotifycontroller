"""Local audio engine — loads and plays audio files through virtual decks.

This is the foundation for real DJ functionality: dual-deck playback,
real-time EQ, crossfader mixing, and effects — all running locally
with sub-millisecond latency.

Dependencies:
  pip install sounddevice soundfile numpy

This module is optional — the app works without it (Spotify-API-only
mode). When available, it enables loading local audio files (MP3, FLAC,
WAV) onto decks for true independent playback.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

try:
    import sounddevice as sd
    import soundfile as sf

    AUDIO_ENGINE_AVAILABLE = True
except ImportError:
    AUDIO_ENGINE_AVAILABLE = False
    _LOGGER.info("sounddevice/soundfile not installed — local audio engine disabled")


@dataclass
class AudioTrack:
    """An audio file loaded into memory for playback."""

    path: Path
    data: np.ndarray  # shape: (samples, channels), dtype: float32
    sample_rate: int
    duration_s: float
    name: str = ""

    @property
    def total_frames(self) -> int:
        return self.data.shape[0]


@dataclass
class AudioDeck:
    """A single audio playback deck with position tracking and EQ."""

    name: str
    track: AudioTrack | None = None
    position: int = 0  # current sample position
    is_playing: bool = False
    volume: float = 1.0  # 0.0 - 1.0
    eq_hi: float = 1.0   # gain multiplier (1.0 = unity)
    eq_mid: float = 1.0
    eq_lo: float = 1.0
    cue_points: dict[int, int] = field(default_factory=dict)  # pad -> sample position

    @property
    def is_loaded(self) -> bool:
        return self.track is not None

    @property
    def position_ms(self) -> int:
        if self.track is None:
            return 0
        return int(self.position / self.track.sample_rate * 1000)

    @property
    def duration_ms(self) -> int:
        if self.track is None:
            return 0
        return int(self.track.duration_s * 1000)

    def seek_ms(self, ms: int) -> None:
        """Seek to a position in milliseconds."""
        if self.track is None:
            return
        sample = int(ms / 1000.0 * self.track.sample_rate)
        self.position = max(0, min(sample, self.track.total_frames - 1))

    def set_cue_point(self, pad: int) -> None:
        """Store current position as a cue point."""
        self.cue_points[pad] = self.position
        _LOGGER.info("AudioDeck %s: cue %d set at sample %d", self.name, pad, self.position)


def load_audio_file(path: str | Path) -> AudioTrack | None:
    """Load an audio file into memory. Returns None if soundfile is unavailable."""
    if not AUDIO_ENGINE_AVAILABLE:
        _LOGGER.error("Audio engine not available — install sounddevice and soundfile")
        return None

    path = Path(path)
    if not path.exists():
        _LOGGER.error("File not found: %s", path)
        return None

    try:
        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
        duration = len(data) / sr
        _LOGGER.info("Loaded: %s (%.1fs, %d Hz, %d ch)", path.name, duration, sr, data.shape[1])
        return AudioTrack(
            path=path,
            data=data,
            sample_rate=sr,
            duration_s=duration,
            name=path.stem,
        )
    except Exception:
        _LOGGER.exception("Failed to load audio file: %s", path)
        return None


class AudioEngine:
    """Real-time audio engine with two decks and a crossfader.

    Mixes audio from two AudioDecks and outputs through the system
    audio device using sounddevice.
    """

    def __init__(self, sample_rate: int = 44100, buffer_size: int = 1024) -> None:
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.deck_a = AudioDeck(name="A")
        self.deck_b = AudioDeck(name="B")
        self.crossfader: float = 0.5  # 0.0 = full A, 1.0 = full B
        self.master_volume: float = 1.0
        self._stream: sd.OutputStream | None = None  # type: ignore[name-defined]
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._stream is not None and self._stream.active

    def start(self) -> None:
        """Start the audio output stream."""
        if not AUDIO_ENGINE_AVAILABLE:
            _LOGGER.error("Cannot start audio engine — sounddevice not installed")
            return
        if self.is_running:
            return

        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=2,
            blocksize=self.buffer_size,
            dtype="float32",
            callback=self._audio_callback,
        )
        self._stream.start()
        _LOGGER.info("Audio engine started (sr=%d, buf=%d)", self.sample_rate, self.buffer_size)

    def stop(self) -> None:
        """Stop the audio output stream."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            _LOGGER.info("Audio engine stopped")

    def load_file(self, deck_name: str, path: str | Path) -> bool:
        """Load an audio file onto a deck."""
        track = load_audio_file(path)
        if track is None:
            return False

        deck = self.deck_a if deck_name == "A" else self.deck_b
        with self._lock:
            deck.track = track
            deck.position = 0
            deck.is_playing = False
            deck.cue_points.clear()
        _LOGGER.info("Deck %s: loaded '%s'", deck_name, track.name)
        return True

    def _read_deck(self, deck: AudioDeck, frames: int) -> np.ndarray:
        """Read frames from a deck, advancing its position."""
        if not deck.is_loaded or not deck.is_playing or deck.track is None:
            return np.zeros((frames, 2), dtype=np.float32)

        track = deck.track
        start = deck.position
        end = min(start + frames, track.total_frames)
        actual = end - start

        if actual <= 0:
            deck.is_playing = False
            return np.zeros((frames, 2), dtype=np.float32)

        chunk = track.data[start:end].copy()

        # Ensure stereo
        if chunk.shape[1] == 1:
            chunk = np.column_stack([chunk, chunk])

        # Apply volume
        chunk *= deck.volume

        # Pad if we hit the end of the track
        if actual < frames:
            pad = np.zeros((frames - actual, 2), dtype=np.float32)
            chunk = np.vstack([chunk, pad])
            deck.is_playing = False

        deck.position = end
        return chunk

    def _audio_callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time_info: object,
        status: object,
    ) -> None:
        """Called by sounddevice for each audio buffer."""
        if status:
            _LOGGER.debug("Audio status: %s", status)

        with self._lock:
            buf_a = self._read_deck(self.deck_a, frames)
            buf_b = self._read_deck(self.deck_b, frames)

        # Crossfader mix
        cf = self.crossfader
        mixed = buf_a * (1.0 - cf) + buf_b * cf
        mixed *= self.master_volume

        # Clip to prevent distortion
        np.clip(mixed, -1.0, 1.0, out=mixed)
        outdata[:] = mixed
