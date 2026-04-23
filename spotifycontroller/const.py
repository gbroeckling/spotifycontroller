"""Constants for SpotifyController."""

from __future__ import annotations

DOMAIN = "spotifycontroller"

# Spotify OAuth
SPOTIFY_SCOPE = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing "
    "playlist-read-private "
    "playlist-read-collaborative "
    "user-library-read"
)
SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"

# Deck identifiers
DECK_A = "A"
DECK_B = "B"

# MIDI defaults
DEFAULT_MIDI_CHANNEL = 0

# Playback
DEFAULT_CROSSFADE_MS = 5000
MIN_VOLUME = 0
MAX_VOLUME = 100

# Controller mapping keys
MAP_PLAY = "play"
MAP_CUE = "cue"
MAP_SYNC = "sync"
MAP_JOG = "jog"
MAP_PITCH = "pitch"
MAP_VOLUME = "volume"
MAP_CROSSFADER = "crossfader"
MAP_EQ_HI = "eq_hi"
MAP_EQ_MID = "eq_mid"
MAP_EQ_LO = "eq_lo"
MAP_LOAD = "load"
MAP_BROWSE = "browse"
MAP_FX1 = "fx1"
MAP_FX2 = "fx2"
MAP_FX3 = "fx3"
MAP_HOTCUE_1 = "hotcue_1"
MAP_HOTCUE_2 = "hotcue_2"
MAP_HOTCUE_3 = "hotcue_3"
MAP_HOTCUE_4 = "hotcue_4"
MAP_LOOP_IN = "loop_in"
MAP_LOOP_OUT = "loop_out"
MAP_NEXT = "next"
MAP_PREV = "prev"
MAP_PFL = "pfl"
MAP_TRIM = "trim"

# Audio engine
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 2
AUDIO_BUFFER_SIZE = 1024

# Supported local audio formats
AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac"}
