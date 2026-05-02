from src.recommender import (
    Song,
    UserProfile,
    Recommender,
    extract_preferences_from_text,
    preferences_to_user_profile,
    recommend_songs_from_text,
)

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    top_song, top_score, top_explanation = results[0]

    assert top_song.genre == "pop"
    assert top_song.mood == "happy"
    assert isinstance(top_score, float)
    assert isinstance(top_explanation, str)
    assert top_explanation.strip()


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


def test_extract_preferences_from_happy_pop_text():
    preferences = extract_preferences_from_text("Play some happy pop music")

    assert preferences.genre == "pop"
    assert preferences.mood == "happy"
    assert preferences.energy == 0.5
    assert preferences.likes_acoustic is False


def test_extract_preferences_from_chill_study_text():
    preferences = extract_preferences_from_text("I want chill lofi songs for studying")

    assert preferences.genre == "lofi"
    assert preferences.mood == "chill"
    assert preferences.energy == 0.4
    assert "lofi" in preferences.search_terms


def test_extract_preferences_falls_back_to_defaults():
    preferences = extract_preferences_from_text("surprise me")
    user_profile = preferences_to_user_profile(preferences)

    assert preferences.genre == ""
    assert preferences.mood == ""
    assert preferences.energy == 0.5
    assert user_profile.favorite_genre == ""
    assert user_profile.favorite_mood == ""
    assert user_profile.target_energy == 0.5


def test_recommend_songs_from_text_returns_explanations():
    songs = [
        {
            "id": 1,
            "title": "Test Pop Track",
            "artist": "Test Artist",
            "genre": "pop",
            "mood": "happy",
            "energy": 0.8,
            "tempo_bpm": 120.0,
            "valence": 0.9,
            "danceability": 0.8,
            "acousticness": 0.2,
        },
        {
            "id": 2,
            "title": "Chill Lofi Loop",
            "artist": "Test Artist",
            "genre": "lofi",
            "mood": "chill",
            "energy": 0.4,
            "tempo_bpm": 80.0,
            "valence": 0.6,
            "danceability": 0.5,
            "acousticness": 0.9,
        },
    ]

    results = recommend_songs_from_text("I want chill lofi songs for studying", songs, k=2)

    assert len(results) == 2
    top_song, top_score, top_explanation = results[0]
    assert top_song["genre"] == "lofi"
    assert isinstance(top_score, float)
    assert top_explanation.strip() != ""
