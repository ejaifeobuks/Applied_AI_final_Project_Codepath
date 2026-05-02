"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.
"""

from recommender import (
    extract_preferences_from_text,
    load_songs,
    recommend_songs,
    recommend_songs_from_text,
)
from spotify_client import SpotifyClient, build_search_query, spotify_track_to_song_dict


def print_recommendations(title: str, recommendations: list[tuple[dict, float, str]]) -> None:
    """Print ranked song recommendations in a consistent CLI format."""
    print()
    print(f"--- {title} ---")
    print()

    if not recommendations:
        print("No recommendations found.")
        return

    for i, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f'  {i}. "{song["title"]}" by {song["artist"]}')
        print(f"     Score: {score:.2f}")
        print(f"     Reason: {explanation}")
        if song.get("album"):
            print(f'     Album: {song["album"]}')
        if song.get("spotify_url"):
            print(f'     Spotify: {song["spotify_url"]}')
        print()


def main() -> None:
    songs = load_songs("data/songs.csv")
    prompt = input(
        "Describe the kind of music you want "
        "(press Enter to run the built-in demo profiles): "
    ).strip()

    if prompt:
        extracted = extract_preferences_from_text(prompt)
        print()
        print("Extracted preferences:")
        print(f"  Genre: {extracted.genre or 'none'}")
        print(f"  Mood: {extracted.mood or 'none'}")
        print(f"  Energy: {extracted.energy:.2f}")
        print(f"  Likes acoustic: {extracted.likes_acoustic}")
        print(f"  Search terms: {', '.join(extracted.search_terms) or 'none'}")

        spotify_client = SpotifyClient()
        if spotify_client.has_credentials():
            query = build_search_query(extracted)
            print(f"  Spotify query: {query}")
            try:
                tracks = spotify_client.search_tracks(query, limit=10)
                spotify_song_dicts = [
                    spotify_track_to_song_dict(track, extracted, fallback_id=index)
                    for index, track in enumerate(tracks, start=1)
                ]
                recommendations = recommend_songs(
                    {
                        "genre": extracted.genre,
                        "mood": extracted.mood,
                        "energy": extracted.energy,
                        "likes_acoustic": extracted.likes_acoustic,
                    },
                    spotify_song_dicts,
                    k=3,
                )
                print_recommendations("Spotify-powered recommendations", recommendations)
                return
            except Exception as exc:
                print(f"Spotify search failed: {exc}")
                print("Falling back to local catalog recommendations.")

        recommendations = recommend_songs_from_text(prompt, songs, k=3)
        print_recommendations("Recommendations from your request", recommendations)
        return

    profiles_to_test = [
        {"name": "Happy Pop Fan", "prefs": {"genre": "pop", "mood": "happy", "energy": 0.8}},
        {"name": "Intense Rock Fan", "prefs": {"genre": "rock", "mood": "intense", "energy": 0.9}},
        {"name": "Chill Lofi Fan", "prefs": {"genre": "lofi", "mood": "chill", "energy": 0.4}},
        {"name": "Peaceful Classical Fan", "prefs": {"genre": "classical", "mood": "peaceful", "energy": 0.2}},
    ]

    for profile in profiles_to_test:
        user_name = profile["name"]
        user_prefs = profile["prefs"]
        recommendations = recommend_songs(user_prefs, songs, k=3)
        print(f"Profile: {user_prefs}")
        print_recommendations(f"Recommendations for: {user_name}", recommendations)


if __name__ == "__main__":
    main()
