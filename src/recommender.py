from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


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
    activity_context: str = ""


@dataclass
class ExtractedPreferences:
    """Structured preferences extracted from a natural-language request."""
    genre: str
    mood: str
    energy: float
    likes_acoustic: bool
    raw_text: str
    search_terms: List[str]
    genres: List[str] = field(default_factory=list)
    moods: List[str] = field(default_factory=list)
    energy_level: str = "medium"
    activity_context: str = ""
    acoustic_preference: str = "neutral"
    extraction_source: str = "keyword"
    is_music_request: bool = True


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
            "genre": 0.20,
            "mood": 0.20,
            "energy": 0.35,
            "acousticness": 0.10,
            "popularity": 0.15,
        }

        scored_songs = []

        for song in self.songs:
            genre_score = 1.0 if song.genre == user.favorite_genre else 0.0
            mood_score = 1.0 if song.mood == user.favorite_mood else 0.0
            energy_score = 1.0 - abs(user.target_energy - song.energy)
            acousticness_score = song.acousticness if user.likes_acoustic else (1.0 - song.acousticness)
            popularity_score = song.popularity / 100.0

            total_score = (
                weights["genre"] * genre_score
                + weights["mood"] * mood_score
                + weights["energy"] * energy_score
                + weights["acousticness"] * acousticness_score
                + weights["popularity"] * popularity_score
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

        if user.activity_context:
            reasons.append(f"suits your {user.activity_context} session")

        if song.genre and song.genre == user.favorite_genre:
            reasons.append(f"matches the {song.genre} genre you requested")

        if song.mood and song.mood == user.favorite_mood:
            reasons.append(f"carries the {song.mood} mood you're looking for")

        energy_diff = abs(user.target_energy - song.energy)
        if energy_diff < 0.1:
            reasons.append("closely matches your energy level")
        elif energy_diff < 0.25:
            reasons.append("has a similar energy level")

        if user.likes_acoustic and song.acousticness >= 0.6:
            reasons.append("has a strong acoustic quality")
        elif not user.likes_acoustic and song.acousticness <= 0.3:
            reasons.append("has a clean produced sound")

        if song.popularity >= 70:
            reasons.append(f"is a well-known track ({song.popularity}/100 popularity)")

        if not reasons:
            return "Matches a combination of your preferences."

        if len(reasons) == 1:
            return f"This track fits because {reasons[0]}."

        return f"This track fits because {', '.join(reasons[:-1])} and {reasons[-1]}."


def _dedupe_terms(terms: List[str]) -> List[str]:
    return list(dict.fromkeys(term for term in terms if term))


def _energy_to_label(energy: float) -> str:
    if energy >= 0.75:
        return "high"
    if energy <= 0.35:
        return "low"
    return "medium"


def _normalize_preferences(
    *,
    raw_text: str,
    genre: str,
    mood: str,
    energy: float,
    likes_acoustic: bool,
    search_terms: List[str],
    genres: Optional[List[str]] = None,
    moods: Optional[List[str]] = None,
    energy_level: str = "",
    activity_context: str = "",
    acoustic_preference: str = "",
    extraction_source: str = "keyword",
    is_music_request: bool = True,
) -> ExtractedPreferences:
    normalized_genres = _dedupe_terms(genres or ([genre] if genre else []))
    normalized_moods = _dedupe_terms(moods or ([mood] if mood else []))
    normalized_search_terms = _dedupe_terms(search_terms)
    resolved_acoustic_preference = acoustic_preference or (
        "prefer" if likes_acoustic else "neutral"
    )

    return ExtractedPreferences(
        genre=genre,
        mood=mood,
        energy=max(0.0, min(1.0, energy)),
        likes_acoustic=likes_acoustic,
        raw_text=raw_text,
        search_terms=normalized_search_terms,
        genres=normalized_genres,
        moods=normalized_moods,
        energy_level=energy_level or _energy_to_label(energy),
        activity_context=activity_context,
        acoustic_preference=resolved_acoustic_preference,
        extraction_source=extraction_source,
        is_music_request=is_music_request,
    )


_NON_MUSIC_PATTERNS = [
    "recipe", "ingredient", "how to cook", "bake",
    "write code", "debug", "fix my", "python script", "javascript",
    "weather", "forecast", "temperature outside",
    "movie", "film recommendation", "tv show", "netflix",
    "book recommendation", "novel", "read me",
    "write a poem", "write an essay", "write a story",
    "math problem", "calculate", "what is 2",
    "sports score", "who won",
    "news", "latest news",
]


def _extract_preferences_keyword_fallback(text: str) -> ExtractedPreferences:
    """Convert a natural-language request into structured recommender inputs."""
    normalized = text.lower().strip()
    is_music_request = not any(pattern in normalized for pattern in _NON_MUSIC_PATTERNS)
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

    activity_context = ""
    if any(term in normalized for term in ["study", "studying", "focus", "focused"]):
        activity_context = "studying"
    elif any(term in normalized for term in ["workout", "gym", "exercise", "run", "running"]):
        activity_context = "workout"
    elif any(term in normalized for term in ["sleep", "bedtime"]):
        activity_context = "sleep"
    elif any(term in normalized for term in ["drive", "driving", "road trip"]):
        activity_context = "driving"

    acoustic_preference = "prefer" if likes_acoustic else "neutral"

    return _normalize_preferences(
        raw_text=text,
        genre=genre,
        mood=mood,
        energy=energy,
        likes_acoustic=likes_acoustic,
        search_terms=search_terms,
        genres=[genre] if genre else [],
        moods=[mood] if mood else [],
        activity_context=activity_context,
        acoustic_preference=acoustic_preference,
        extraction_source="keyword",
        is_music_request=is_music_request,
    )


def _normalize_openai_payload(text: str, payload: Dict[str, Any]) -> ExtractedPreferences:
    is_music_request = bool(payload.get("is_music_request", True))
    genres = [str(item).strip().lower() for item in payload.get("genres", []) if str(item).strip()]
    moods = [str(item).strip().lower() for item in payload.get("moods", []) if str(item).strip()]
    search_terms = [
        str(item).strip().lower()
        for item in payload.get("search_terms", [])
        if str(item).strip()
    ]
    activity_context = str(payload.get("activity_context", "")).strip().lower()
    energy_level = str(payload.get("energy_level", "")).strip().lower()
    acoustic_preference = str(payload.get("acoustic_preference", "")).strip().lower()

    energy_lookup = {"low": 0.25, "medium": 0.5, "high": 0.85}
    energy = energy_lookup.get(energy_level, 0.5)
    likes_acoustic = acoustic_preference == "prefer"

    if activity_context and activity_context not in search_terms:
        search_terms.append(activity_context)

    return _normalize_preferences(
        raw_text=text,
        genre=genres[0] if genres else "",
        mood=moods[0] if moods else "",
        energy=energy,
        likes_acoustic=likes_acoustic,
        search_terms=search_terms + genres + moods,
        genres=genres,
        moods=moods,
        energy_level=energy_level,
        activity_context=activity_context,
        acoustic_preference=acoustic_preference or "neutral",
        extraction_source="openai",
        is_music_request=is_music_request,
    )


def _extract_preferences_with_openai(
    text: str,
    openai_client: Any,
    model: str = "gpt-4.1-mini",
) -> ExtractedPreferences:
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "music_preferences",
            "schema": {
                "type": "object",
                "properties": {
                    "is_music_request": {"type": "boolean"},
                    "genres": {"type": "array", "items": {"type": "string"}},
                    "moods": {"type": "array", "items": {"type": "string"}},
                    "energy_level": {"type": "string", "enum": ["low", "medium", "high"]},
                    "activity_context": {"type": "string"},
                    "acoustic_preference": {
                        "type": "string",
                        "enum": ["prefer", "avoid", "neutral"],
                    },
                    "search_terms": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "is_music_request",
                    "genres",
                    "moods",
                    "energy_level",
                    "activity_context",
                    "acoustic_preference",
                    "search_terms",
                ],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }

    response = openai_client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a music preference extractor. "
                    "Set is_music_request to false if the user is NOT asking for music "
                    "recommendations (e.g. asking for recipes, coding help, math, weather, "
                    "movies, jokes, or anything unrelated to finding songs). "
                    "Otherwise set it to true and extract the remaining fields."
                ),
            },
            {"role": "user", "content": text},
        ],
        response_format=response_format,
    )
    content = response.choices[0].message.content
    payload = json.loads(content)
    if not payload:
        raise ValueError("OpenAI response did not contain structured preference data.")
    return _normalize_openai_payload(text, payload)


def _build_openai_client() -> Any:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    return OpenAI(api_key=api_key)


def extract_preferences_from_text(
    text: str,
    openai_client: Any = None,
    use_openai: bool = True,
    model: str = "gpt-4.1-mini",
) -> ExtractedPreferences:
    if use_openai:
        client = openai_client if openai_client is not None else _build_openai_client()
        if client is not None:
            try:
                return _extract_preferences_with_openai(text, client, model=model)
            except Exception as exc:
                print(f"OpenAI extraction failed, using keyword fallback: {exc}", file=sys.stderr)

    return _extract_preferences_keyword_fallback(text)


def preferences_to_user_profile(preferences: ExtractedPreferences) -> UserProfile:
    """Adapt extracted text preferences to the recommender's profile shape."""
    return UserProfile(
        favorite_genre=preferences.genre,
        favorite_mood=preferences.mood,
        target_energy=preferences.energy,
        likes_acoustic=preferences.likes_acoustic,
        activity_context=preferences.activity_context,
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
