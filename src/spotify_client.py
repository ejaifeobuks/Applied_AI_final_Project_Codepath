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
        self.client_id = (client_id or os.getenv("SPOTIFY_CLIENT_ID", "")).strip()
        self.client_secret = (client_secret or os.getenv("SPOTIFY_CLIENT_SECRET", "")).strip()

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

        def _fetch(q: str) -> List[SpotifyTrack]:
            response = requests.get(
                SEARCH_URL,
                headers={"Authorization": f"Bearer {token}"},
                params={"q": q, "type": "track", "limit": min(limit, 10)},
                timeout=10,
            )
            response.raise_for_status()
            items = response.json().get("tracks", {}).get("items", [])
            return [self._normalize_track(item) for item in items]

        try:
            return _fetch(query)
        except requests.HTTPError as exc:
            first_term = query.split()[0] if query else ""
            if exc.response.status_code == 400 and first_term and first_term != query:
                return _fetch(first_term)
            raise

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
    """Build a Spotify search query from extracted user preferences.

    Enriches the query using the genre knowledge base when available —
    replacing a bare genre name with curated Spotify search terms drawn from
    genre_profiles.json. Falls back to the raw genre/mood/activity signals
    when the genre is not in the KB.

    Returns an empty string when no signals are present, signalling the caller
    to skip the Spotify path and fall back to the local catalog.
    """
    try:
        from knowledge_base import enrich_search_terms
    except ImportError:
        from src.knowledge_base import enrich_search_terms

    if not preferences.genre and not preferences.mood and not preferences.activity_context:
        return ""

    terms = enrich_search_terms(
        preferences.genre,
        preferences.mood,
        preferences.activity_context,
    )
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
