from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from recommender import ExtractedPreferences


TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"


@dataclass
class SpotifyTrack:
    title: str
    artist: str
    album: str
    spotify_url: str
    preview_url: Optional[str]
    popularity: int


class SpotifyClient:
    """Small wrapper around Spotify client-credentials auth and track search."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> None:
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET", "")

    def has_credentials(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_access_token(self) -> str:
        if not self.has_credentials():
            raise ValueError("Missing Spotify credentials.")

        response = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise ValueError("Spotify token response did not include an access token.")
        return token

    def search_tracks(self, query: str, limit: int = 10) -> List[SpotifyTrack]:
        token = self.get_access_token()
        response = requests.get(
            SEARCH_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "type": "track", "limit": min(limit, 10)},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("tracks", {}).get("items", [])
        return [self._normalize_track(item) for item in items]

    @staticmethod
    def _normalize_track(item: dict) -> SpotifyTrack:
        artists = item.get("artists", [])
        first_artist = artists[0]["name"] if artists else "Unknown Artist"
        return SpotifyTrack(
            title=item.get("name", "Unknown Title"),
            artist=first_artist,
            album=item.get("album", {}).get("name", "Unknown Album"),
            spotify_url=item.get("external_urls", {}).get("spotify", ""),
            preview_url=item.get("preview_url"),
            popularity=item.get("popularity", 0),
        )


def build_search_query(preferences: "ExtractedPreferences") -> str:
    """Build a Spotify search query from extracted user preferences."""
    terms = list(preferences.search_terms)
    if preferences.genre and preferences.genre not in terms:
        terms.append(preferences.genre)
    if preferences.mood and preferences.mood not in terms:
        terms.append(preferences.mood)
    if not terms:
        terms.append(preferences.raw_text.strip() or "music")
    return " ".join(terms)


def spotify_track_to_song_dict(
    track: SpotifyTrack,
    preferences: "ExtractedPreferences",
    fallback_id: int,
) -> dict:
    """Convert a Spotify track into the local song shape used by the recommender."""
    return {
        "id": fallback_id,
        "title": track.title,
        "artist": track.artist,
        "genre": preferences.genre,
        "mood": preferences.mood,
        "energy": preferences.energy,
        "tempo_bpm": 0.0,
        "valence": 0.5,
        "danceability": 0.5,
        "acousticness": 0.7 if preferences.likes_acoustic else 0.5,
        "album": track.album,
        "spotify_url": track.spotify_url,
        "preview_url": track.preview_url,
        "popularity": track.popularity,
    }
