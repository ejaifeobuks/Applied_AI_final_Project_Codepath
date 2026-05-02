from unittest.mock import Mock, patch

import pytest

from src.recommender import extract_preferences_from_text
from src.spotify_client import (
    SEARCH_URL,
    TOKEN_URL,
    SpotifyClient,
    build_search_query,
    spotify_track_to_song_dict,
)


def test_get_access_token_raises_without_credentials():
    client = SpotifyClient(client_id="", client_secret="")

    with pytest.raises(ValueError, match="Missing Spotify credentials"):
        client.get_access_token()


@patch("src.spotify_client.requests.post")
def test_get_access_token_returns_token(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {"access_token": "token-123"}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    client = SpotifyClient(client_id="abc", client_secret="xyz")
    token = client.get_access_token()

    assert token == "token-123"
    mock_post.assert_called_once_with(
        TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=("abc", "xyz"),
        timeout=10,
    )


@patch("src.spotify_client.requests.get")
@patch.object(SpotifyClient, "get_access_token", return_value="token-123")
def test_search_tracks_returns_normalized_tracks(mock_get_token, mock_get):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "tracks": {
            "items": [
                {
                    "name": "Song A",
                    "artists": [{"name": "Artist A"}],
                    "album": {"name": "Album A"},
                    "external_urls": {"spotify": "https://spotify.test/song-a"},
                    "preview_url": "https://preview.test/song-a.mp3",
                    "popularity": 87,
                }
            ]
        }
    }
    mock_get.return_value = mock_response

    client = SpotifyClient(client_id="abc", client_secret="xyz")
    results = client.search_tracks("happy pop", limit=20)

    assert len(results) == 1
    assert results[0].title == "Song A"
    assert results[0].artist == "Artist A"
    assert results[0].album == "Album A"
    assert results[0].spotify_url == "https://spotify.test/song-a"
    assert results[0].preview_url == "https://preview.test/song-a.mp3"
    assert results[0].popularity == 87
    mock_get_token.assert_called_once()
    mock_get.assert_called_once_with(
        SEARCH_URL,
        headers={"Authorization": "Bearer token-123"},
        params={"q": "happy pop", "type": "track", "limit": 10},
        timeout=10,
    )


def test_build_search_query_uses_extracted_terms():
    preferences = extract_preferences_from_text("happy pop music")
    query = build_search_query(preferences)

    # KB-enriched query should contain genre-specific Spotify search terms,
    # not just the bare genre name "pop".
    assert "pop" in query
    assert query != "pop"                  # KB must have added more terms
    assert len(query.split()) >= 2         # at least two tokens in the enriched query


def test_build_search_query_kb_enrichment_improves_bare_genre():
    """Verify KB enrichment produces a richer query than genre+mood alone."""
    from src.recommender import ExtractedPreferences

    bare_prefs = ExtractedPreferences(
        genre="lofi", mood="chill", energy=0.4,
        likes_acoustic=False, raw_text="lofi chill", search_terms=[],
    )
    query = build_search_query(bare_prefs)

    # KB should expand "lofi" to include curated Spotify search terms
    assert "lofi" in query
    assert query != "lofi chill"           # enrichment changed the query
    assert len(query.split()) > 2          # more than just genre + mood


def test_spotify_track_to_song_dict_preserves_metadata():
    preferences = extract_preferences_from_text("chill acoustic music")
    track = Mock(
        title="Song A",
        artist="Artist A",
        album="Album A",
        spotify_url="https://spotify.test/song-a",
        preview_url="https://preview.test/song-a.mp3",
        popularity=87,
    )

    song_dict = spotify_track_to_song_dict(track, preferences, fallback_id=99)

    assert song_dict["id"] == 99
    assert song_dict["title"] == "Song A"
    assert song_dict["artist"] == "Artist A"
    assert song_dict["album"] == "Album A"
    assert song_dict["spotify_url"] == "https://spotify.test/song-a"
    assert song_dict["preview_url"] == "https://preview.test/song-a.mp3"
    assert song_dict["mood"] == "chill"
