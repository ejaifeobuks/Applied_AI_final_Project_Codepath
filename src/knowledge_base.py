
from __future__ import annotations

import json
import pathlib
from typing import Optional

_KB_PATH = pathlib.Path(__file__).parent.parent / "data" / "genre_profiles.json"
_PROFILES: Optional[dict] = None


def _load() -> dict:
    global _PROFILES
    if _PROFILES is None:
        with open(_KB_PATH, encoding="utf-8") as f:
            _PROFILES = json.load(f)
    return _PROFILES


def get_genre_profile(genre: str) -> Optional[dict]:
    """Return the full knowledge-base profile for a genre, or None if not found."""
    if not genre:
        return None
    return _load().get(genre.lower().strip())


def enrich_search_terms(genre: str, mood: str, activity_context: str) -> list[str]:
    """Return KB-enriched Spotify search terms for the given signals.

    Uses the genre's curated spotify_search_terms as the primary query
    source, then appends the mood and activity when they add specificity.
    Falls back to the raw signals when the genre is not in the KB.
    """
    profile = get_genre_profile(genre)
    terms: list[str] = []

    if profile:
        kb_terms = profile.get("spotify_search_terms", [])
        terms.extend(kb_terms[:2])
        if mood and mood in profile.get("common_moods", []) and mood not in terms:
            terms.append(mood)
    else:
        if genre:
            terms.append(genre)
        if mood:
            terms.append(mood)

    if activity_context and activity_context not in terms:
        terms.append(activity_context)

    return terms


def get_genre_description(genre: str) -> str:
    """Return the first sentence of the genre description, or empty string."""
    profile = get_genre_profile(genre)
    if not profile:
        return ""
    description = profile.get("description", "")
    return description.split(".")[0] + "." if description else ""


def get_related_genres(genre: str) -> list[str]:
    """Return a list of related genres from the KB."""
    profile = get_genre_profile(genre)
    if not profile:
        return []
    return profile.get("related_genres", [])


def get_typical_energy_range(genre: str) -> Optional[tuple[float, float]]:
    """Return the (min, max) typical energy range for a genre."""
    profile = get_genre_profile(genre)
    if not profile:
        return None
    r = profile.get("typical_energy_range")
    if r and len(r) == 2:
        return (float(r[0]), float(r[1]))
    return None
