"""Mixxx library manager — add, import, and organize tracks in Mixxx's SQLite database.

Mixxx stores its track library in a SQLite database (mixxxdb.sqlite).
This module provides tools to:
  - Scan a folder and import all audio files into Mixxx's library
  - Add individual tracks with metadata
  - Create and manage crates (DJ folders)
  - Query the library for tracks

This lets SpotifyController feed tracks into Mixxx's library so they
show up immediately in Mixxx's browser.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from spotifycontroller.const import AUDIO_EXTENSIONS
from spotifycontroller.mixxx.integration import get_db_path

_LOGGER = logging.getLogger(__name__)


@dataclass
class MixxxTrack:
    """A track as stored in Mixxx's library."""

    id: int
    title: str
    artist: str
    album: str
    duration: float  # seconds
    bpm: float
    key: str
    file_path: str
    sample_rate: int = 44100
    channels: int = 2
    bitrate: int = 320


class MixxxLibrary:
    """Interface to Mixxx's SQLite track library."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or get_db_path()
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            if not self._db_path.exists():
                raise FileNotFoundError(
                    f"Mixxx database not found at {self._db_path}. "
                    "Run Mixxx at least once to create it."
                )
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # -- Track operations --

    def track_exists(self, file_path: str) -> bool:
        """Check if a track with this file path is already in the library."""
        conn = self._connect()
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM track_locations
            WHERE location = ?
            """,
            (file_path,),
        )
        return cursor.fetchone()[0] > 0

    def add_track(
        self,
        file_path: str,
        title: str = "",
        artist: str = "",
        album: str = "",
        duration: float = 0.0,
        bpm: float = 0.0,
        key: str = "",
        sample_rate: int = 44100,
        channels: int = 2,
        bitrate: int = 320,
    ) -> int | None:
        """Add a track to Mixxx's library. Returns the library row ID or None if it exists."""
        abs_path = str(Path(file_path).resolve())

        if self.track_exists(abs_path):
            _LOGGER.debug("Track already in library: %s", abs_path)
            return None

        conn = self._connect()
        directory = str(Path(abs_path).parent)
        filename = Path(abs_path).name
        filesize = os.path.getsize(abs_path) if Path(abs_path).exists() else 0

        if not title:
            title = Path(abs_path).stem

        try:
            # Insert into track_locations
            cursor = conn.execute(
                """
                INSERT INTO track_locations
                    (location, filename, directory, filesize, fs_deleted, needs_verification)
                VALUES (?, ?, ?, ?, 0, 0)
                """,
                (abs_path, filename, directory, filesize),
            )
            location_id = cursor.lastrowid

            # Insert into library
            cursor = conn.execute(
                """
                INSERT INTO library
                    (artist, title, album, duration, bpm, key,
                     samplerate, channels, bitrate,
                     location, mixxx_deleted, played)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
                """,
                (
                    artist, title, album, duration, bpm, key,
                    sample_rate, channels, bitrate,
                    location_id,
                ),
            )
            library_id = cursor.lastrowid
            conn.commit()
            _LOGGER.info("Added to Mixxx library: %s — %s (id=%d)", artist, title, library_id)
            return library_id

        except sqlite3.Error:
            conn.rollback()
            _LOGGER.exception("Failed to add track: %s", abs_path)
            return None

    def import_folder(self, folder: str | Path, recursive: bool = True) -> int:
        """Scan a folder and import all audio files into Mixxx's library.

        Returns the number of tracks imported.
        """
        folder = Path(folder)
        if not folder.is_dir():
            _LOGGER.error("Not a directory: %s", folder)
            return 0

        count = 0
        pattern = "**/*" if recursive else "*"
        for f in sorted(folder.glob(pattern)):
            if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS:
                result = self.add_track(str(f), title=f.stem)
                if result is not None:
                    count += 1

        _LOGGER.info("Imported %d tracks from %s", count, folder)
        return count

    def search_tracks(self, query: str, limit: int = 20) -> list[MixxxTrack]:
        """Search Mixxx library by title or artist."""
        conn = self._connect()
        cursor = conn.execute(
            """
            SELECT l.id, l.title, l.artist, l.album, l.duration, l.bpm, l.key,
                   tl.location, l.samplerate, l.channels, l.bitrate
            FROM library l
            JOIN track_locations tl ON l.location = tl.id
            WHERE (l.title LIKE ? OR l.artist LIKE ?)
              AND l.mixxx_deleted = 0
            ORDER BY l.artist, l.title
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", limit),
        )
        return [
            MixxxTrack(
                id=row["id"],
                title=row["title"] or "",
                artist=row["artist"] or "",
                album=row["album"] or "",
                duration=row["duration"] or 0.0,
                bpm=row["bpm"] or 0.0,
                key=row["key"] or "",
                file_path=row["location"] or "",
                sample_rate=row["samplerate"] or 44100,
                channels=row["channels"] or 2,
                bitrate=row["bitrate"] or 320,
            )
            for row in cursor.fetchall()
        ]

    def get_track_count(self) -> int:
        """Return the total number of active tracks in the library."""
        conn = self._connect()
        cursor = conn.execute(
            "SELECT COUNT(*) FROM library WHERE mixxx_deleted = 0"
        )
        return cursor.fetchone()[0]

    # -- Crate operations --

    def create_crate(self, name: str) -> int | None:
        """Create a crate (DJ folder). Returns the crate ID."""
        conn = self._connect()
        try:
            cursor = conn.execute(
                "INSERT INTO crates (name, count, show) VALUES (?, 0, 1)",
                (name,),
            )
            conn.commit()
            crate_id = cursor.lastrowid
            _LOGGER.info("Created crate: %s (id=%d)", name, crate_id)
            return crate_id
        except sqlite3.IntegrityError:
            _LOGGER.debug("Crate already exists: %s", name)
            cursor = conn.execute("SELECT id FROM crates WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row["id"] if row else None

    def add_track_to_crate(self, crate_id: int, track_id: int) -> bool:
        """Add a track to a crate."""
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO crate_tracks (crate_id, track_id) VALUES (?, ?)",
                (crate_id, track_id),
            )
            conn.execute(
                "UPDATE crates SET count = count + 1 WHERE id = ?",
                (crate_id,),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Already in crate

    def list_crates(self) -> list[tuple[int, str, int]]:
        """Return all crates as (id, name, track_count) tuples."""
        conn = self._connect()
        cursor = conn.execute("SELECT id, name, count FROM crates ORDER BY name")
        return [(row["id"], row["name"], row["count"]) for row in cursor.fetchall()]

    def import_folder_to_crate(self, folder: str | Path, crate_name: str | None = None) -> int:
        """Import a folder into the library and add all tracks to a crate.

        If crate_name is None, uses the folder name.
        Returns the number of tracks imported.
        """
        folder = Path(folder)
        crate_name = crate_name or folder.name
        crate_id = self.create_crate(crate_name)
        if crate_id is None:
            return 0

        count = 0
        for f in sorted(folder.rglob("*")):
            if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS:
                abs_path = str(f.resolve())
                track_id = self.add_track(abs_path, title=f.stem)
                if track_id is not None:
                    self.add_track_to_crate(crate_id, track_id)
                    count += 1

        _LOGGER.info("Imported %d tracks into crate '%s'", count, crate_name)
        return count
