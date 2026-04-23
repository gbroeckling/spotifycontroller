"""Spotify OAuth authentication.

Uses the Authorization Code flow via spotipy's built-in OAuth manager.
On first run this opens a browser for the user to authorize. The token
is cached locally so subsequent runs skip the browser.
"""

from __future__ import annotations

import logging
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from spotifycontroller.const import SPOTIFY_REDIRECT_URI, SPOTIFY_SCOPE

_LOGGER = logging.getLogger(__name__)

_TOKEN_CACHE = Path.home() / ".spotifycontroller" / ".spotify_token_cache"


def create_spotify_client(client_id: str, client_secret: str) -> spotipy.Spotify:
    """Create and return an authenticated Spotify client.

    The first call opens a browser for user authorization. Subsequent calls
    use the cached token (refreshing automatically when expired).
    """
    _TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE,
        cache_path=str(_TOKEN_CACHE),
        open_browser=True,
    )

    sp = spotipy.Spotify(auth_manager=auth_manager)
    _LOGGER.info("Spotify client authenticated")
    return sp
