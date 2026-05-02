from typing import List, Dict, Tuple, Optional
import csv
from dataclasses import dataclass


GENRE_KEYWORDS = {
    "pop": "pop",
    "rock": "rock",
    "lofi": "lofi",
    "lo-fi": "lofi",
    "classical": "classical",
    "ambient": "ambient",
    "jazz": "jazz",
    "synthwave": "synthwave",
    "country": "country",
    "hip-hop": "hip-hop",
    "hip hop": "hip-hop",
    "reggae": "reggae",
    "electronic": "electronic",
    "folk": "folk",
    "acoustic": "acoustic",
    "indie": "indie pop",
}

MOOD_KEYWORDS = {
    "happy": "happy",
    "chill": "chill",
    "intense": "intense",
    "peaceful": "peaceful",
    "relaxed": "relaxed",
    "moody": "moody",
    "focused": "focused",
    "romantic": "romantic",
    "sad": "sad",
    "groovy": "groovy",
    "epic": "epic",
    "driving": "driving",
}


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    album: str = ""
    spotify_url: str = ""
    preview_url: Optional[str] = None
    popularity: int = 0


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


@dataclass
class ExtractedPreferences:
    """Structured preferences extracted from a natural-language request."""
    genre: str
    mood: str
    energy: float
    likes_acoustic: bool
    raw_text: str
    search_terms: List[str]


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        """Store the songs available for recommendation."""
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Tuple[Song, float, str]]:
        """Rank songs for a user and return the top matches with explanations."""
        weights = {
            "genre": 0.2,
            "mood": 0.3,
            "energy": 0.5,
        }

        scored_songs = []

        for song in self.songs:
            genre_score = 1.0 if song.genre == user.favorite_genre else 0.0
            mood_score = 1.0 if song.mood == user.favorite_mood else 0.0
            energy_score = 1 - abs(user.target_energy - song.energy)

            total_score = (
                weights["genre"] * genre_score +
                weights["mood"] * mood_score +
                weights["energy"] * energy_score
            )
            scored_songs.append((song, total_score))

        scored_songs.sort(key=lambda x: x[1], reverse=True)
        top_k_songs = scored_songs[:k]

        recommendations_with_explanations = []
        for song, score in top_k_songs:
            explanation = self.explain_recommendation(user, song)
            recommendations_with_explanations.append((song, score, explanation))

        return recommendations_with_explanations

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Explain why a song matches a user's preferences."""
        reasons = []

        if song.genre == user.favorite_genre:
            reasons.append(f"it's in the '{song.genre}' genre you like")

        if song.mood == user.favorite_mood:
            reasons.append(f"it has the '{song.mood}' mood you're looking for")

        energy_diff = abs(user.target_energy - song.energy)
        if energy_diff < 0.1:
            reasons.append("it has a very similar energy level")
        elif energy_diff < 0.2:
            reasons.append("it has a similar energy level")

        if not reasons:
            return "It's a potential match based on a combination of factors."

        explanation = "Because " + " and ".join(reasons) + "."
        return explanation.capitalize()


def extract_preferences_from_text(text: str) -> ExtractedPreferences:
    """Convert a natural-language request into structured recommender inputs."""
    normalized = text.lower().strip()
    genre = ""
    mood = ""
    energy = 0.5
    likes_acoustic = False
    search_terms: List[str] = []

    for keyword, mapped_genre in GENRE_KEYWORDS.items():
        if keyword in normalized:
            genre = mapped_genre
            search_terms.append(mapped_genre)
            break

    for keyword, mapped_mood in MOOD_KEYWORDS.items():
        if keyword in normalized:
            mood = mapped_mood
            search_terms.append(mapped_mood)
            break

    if any(term in normalized for term in ["workout", "gym", "high energy", "energetic", "upbeat"]):
        energy = 0.9
    elif any(term in normalized for term in ["study", "studying", "focus", "focused"]):
        energy = 0.4
        if not mood:
            mood = "focused"
            search_terms.append(mood)
    elif any(term in normalized for term in ["calm", "sleep", "soft", "quiet"]):
        energy = 0.2
    elif any(term in normalized for term in ["dance", "party", "drive", "driving"]):
        energy = 0.75

    if any(term in normalized for term in ["acoustic", "guitar", "piano", "soft"]):
        likes_acoustic = True
        if "acoustic" not in search_terms:
            search_terms.append("acoustic")

    return ExtractedPreferences(
        genre=genre,
        mood=mood,
        energy=energy,
        likes_acoustic=likes_acoustic,
        raw_text=text,
        search_terms=search_terms,
    )


def preferences_to_user_profile(preferences: ExtractedPreferences) -> UserProfile:
    """Adapt extracted text preferences to the recommender's profile shape."""
    return UserProfile(
        favorite_genre=preferences.genre,
        favorite_mood=preferences.mood,
        target_energy=preferences.energy,
        likes_acoustic=preferences.likes_acoustic,
    )


def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from a CSV file and convert numeric fields."""
    songs = []
    with open(csv_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                row['id'] = int(row['id'])
                row['energy'] = float(row['energy'])
                row['tempo_bpm'] = float(row['tempo_bpm'])
                row['valence'] = float(row['valence'])
                row['danceability'] = float(row['danceability'])
                row['acousticness'] = float(row['acousticness'])
                songs.append(row)
            except (ValueError, KeyError) as e:
                print(f"Skipping row due to error: {e} in row {row}")
    return songs


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Convert raw data into objects, score songs, and return formatted recommendations."""
    song_objects = [Song(**s) for s in songs]
    user_profile = UserProfile(
        favorite_genre=user_prefs.get("genre", ""),
        favorite_mood=user_prefs.get("mood", ""),
        target_energy=user_prefs.get("energy", 0.5),
        likes_acoustic=user_prefs.get("likes_acoustic", False),
    )

    recommender = Recommender(song_objects)
    recommendations = recommender.recommend(user_profile, k)

    final_results = []
    for song_obj, score, explanation in recommendations:
        song_dict = {
            'id': song_obj.id,
            'title': song_obj.title,
            'artist': song_obj.artist,
            'genre': song_obj.genre,
            'mood': song_obj.mood,
            'energy': song_obj.energy,
            'tempo_bpm': song_obj.tempo_bpm,
            'valence': song_obj.valence,
            'danceability': song_obj.danceability,
            'acousticness': song_obj.acousticness,
            'album': song_obj.album,
            'spotify_url': song_obj.spotify_url,
            'preview_url': song_obj.preview_url,
            'popularity': song_obj.popularity,
        }
        final_results.append((song_dict, score, explanation))

    return final_results


def recommend_songs_from_text(
    text: str,
    songs: List[Dict],
    k: int = 5,
) -> List[Tuple[Dict, float, str]]:
    """Generate recommendations from a natural-language request."""
    preferences = extract_preferences_from_text(text)
    user_profile = preferences_to_user_profile(preferences)
    return recommend_songs(
        {
            "genre": user_profile.favorite_genre,
            "mood": user_profile.favorite_mood,
            "energy": user_profile.target_energy,
            "likes_acoustic": user_profile.likes_acoustic,
        },
        songs,
        k=k,
    )
