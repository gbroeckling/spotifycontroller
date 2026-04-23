"""Mixxx integration — detection, launch, mapping installation, and audio routing.

Mixxx is the open-source DJ engine that does the actual audio work: dual-deck
playback, beat sync, EQ, effects, waveforms. SpotifyController acts as the
orchestrator: it handles Spotify browsing, audio capture/routing, and ties
everything together.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

# Standard Mixxx paths on Windows
_MIXXX_USER_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "Mixxx"
_MIXXX_CONTROLLERS_DIR = _MIXXX_USER_DIR / "controllers"
_MIXXX_DB_PATH = _MIXXX_USER_DIR / "mixxxdb.sqlite"

# Where our bundled files live (relative to repo root)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BUNDLED_MAPPINGS = _REPO_ROOT / "mappings" / "mixxx"
_BUNDLED_SKINS = _REPO_ROOT / "skins"

# Mixxx user skins directory
_MIXXX_SKINS_DIR = _MIXXX_USER_DIR / "skins"

# Common Mixxx install locations
_MIXXX_INSTALL_PATHS = [
    Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Mixxx",
    Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Mixxx",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Mixxx",
]


def find_mixxx_executable() -> Path | None:
    """Locate the Mixxx executable on this system."""
    # Check PATH first
    mixxx_on_path = shutil.which("mixxx")
    if mixxx_on_path:
        return Path(mixxx_on_path)

    # Check standard install locations
    for base in _MIXXX_INSTALL_PATHS:
        exe = base / "mixxx.exe"
        if exe.exists():
            return exe

    return None


def is_mixxx_installed() -> bool:
    """Check whether Mixxx is installed."""
    return find_mixxx_executable() is not None


def get_mixxx_version(exe: Path | None = None) -> str | None:
    """Get the installed Mixxx version string."""
    exe = exe or find_mixxx_executable()
    if exe is None:
        return None
    try:
        result = subprocess.run(
            [str(exe), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Mixxx prints version to stdout or stderr
        output = result.stdout.strip() or result.stderr.strip()
        for line in output.splitlines():
            if "mixxx" in line.lower():
                return line.strip()
        return output.splitlines()[0] if output else None
    except Exception:
        _LOGGER.debug("Could not get Mixxx version", exc_info=True)
        return None


def get_user_data_dir() -> Path:
    """Return the Mixxx user data directory, creating it if needed."""
    _MIXXX_USER_DIR.mkdir(parents=True, exist_ok=True)
    return _MIXXX_USER_DIR


def get_controllers_dir() -> Path:
    """Return the Mixxx user controllers directory, creating it if needed."""
    _MIXXX_CONTROLLERS_DIR.mkdir(parents=True, exist_ok=True)
    return _MIXXX_CONTROLLERS_DIR


def get_db_path() -> Path:
    """Return the path to Mixxx's SQLite database."""
    return _MIXXX_DB_PATH


def install_controller_mapping() -> bool:
    """Copy the bundled VCI-380 mapping files into Mixxx's user controllers dir.

    Returns True if files were installed successfully.
    """
    dest_dir = get_controllers_dir()
    installed = []

    if not _BUNDLED_MAPPINGS.exists():
        _LOGGER.error("Bundled mappings not found at %s", _BUNDLED_MAPPINGS)
        return False

    for src_file in _BUNDLED_MAPPINGS.iterdir():
        if src_file.suffix in (".xml", ".js"):
            dest = dest_dir / src_file.name
            shutil.copy2(src_file, dest)
            installed.append(src_file.name)
            _LOGGER.info("Installed mapping: %s → %s", src_file.name, dest)

    if installed:
        _LOGGER.info("Installed %d mapping file(s) to %s", len(installed), dest_dir)
        return True

    _LOGGER.warning("No mapping files found in %s", _BUNDLED_MAPPINGS)
    return False


def get_skins_dir() -> Path:
    """Return the Mixxx user skins directory, creating it if needed."""
    _MIXXX_SKINS_DIR.mkdir(parents=True, exist_ok=True)
    return _MIXXX_SKINS_DIR


def list_bundled_skins() -> list[str]:
    """Return names of skins bundled with SpotifyController."""
    if not _BUNDLED_SKINS.exists():
        return []
    return [d.name for d in _BUNDLED_SKINS.iterdir() if d.is_dir() and (d / "skin.xml").exists()]


def install_skin(skin_name: str | None = None) -> bool:
    """Copy a bundled skin into Mixxx's user skins directory.

    If skin_name is None, installs all bundled skins.
    Returns True if at least one skin was installed.
    """
    dest_dir = get_skins_dir()
    available = list_bundled_skins()

    if not available:
        _LOGGER.error("No bundled skins found in %s", _BUNDLED_SKINS)
        return False

    to_install = [skin_name] if skin_name else available
    installed = []

    for name in to_install:
        src = _BUNDLED_SKINS / name
        if not src.exists() or not (src / "skin.xml").exists():
            _LOGGER.warning("Skin not found or invalid: %s", name)
            continue

        dest = dest_dir / name
        if dest.exists():
            shutil.rmtree(dest)

        shutil.copytree(src, dest)
        installed.append(name)
        _LOGGER.info("Installed skin: %s → %s", name, dest)

    if installed:
        _LOGGER.info("Installed %d skin(s) to %s", len(installed), dest_dir)
        return True

    return False


def is_skin_installed(skin_name: str) -> bool:
    """Check if a skin is installed in Mixxx's user skins directory."""
    return (get_skins_dir() / skin_name / "skin.xml").exists()


def launch_mixxx(exe: Path | None = None) -> subprocess.Popen | None:
    """Launch Mixxx as a subprocess."""
    exe = exe or find_mixxx_executable()
    if exe is None:
        _LOGGER.error("Mixxx executable not found")
        return None

    _LOGGER.info("Launching Mixxx: %s", exe)
    try:
        proc = subprocess.Popen(
            [str(exe)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return proc
    except Exception:
        _LOGGER.exception("Failed to launch Mixxx")
        return None


def print_setup_status() -> None:
    """Print a summary of Mixxx installation and configuration status."""
    exe = find_mixxx_executable()
    print("\n=== Mixxx Setup Status ===")

    if exe:
        version = get_mixxx_version(exe)
        print(f"  Mixxx found:    {exe}")
        print(f"  Version:        {version or 'unknown'}")
    else:
        print("  Mixxx:          NOT FOUND")
        print("  Install from:   https://mixxx.org/download/")
        if sys.platform == "win32":
            print("  Or run:         winget install Mixxx.Mixxx")

    db = get_db_path()
    print(f"  Database:       {'exists' if db.exists() else 'not found (run Mixxx once first)'}")
    print(f"  User data:      {get_user_data_dir()}")
    print(f"  Controllers:    {get_controllers_dir()}")

    # Check if our mapping is installed
    ctrl_dir = get_controllers_dir()
    mapping_xml = ctrl_dir / "Vestax-VCI-380.midi.xml"
    if mapping_xml.exists():
        print("  VCI-380 map:    INSTALLED")
    else:
        print("  VCI-380 map:    not installed (run 'install-mapping')")

    # Check skins
    skins_dir = get_skins_dir()
    bundled = list_bundled_skins()
    print(f"  Skins dir:      {skins_dir}")
    print(f"  Bundled skins:  {', '.join(bundled) if bundled else 'none'}")
    for name in bundled:
        status = "INSTALLED" if is_skin_installed(name) else "not installed"
        print(f"    {name}: {status}")

    print("==========================\n")
