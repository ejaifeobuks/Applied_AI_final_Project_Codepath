import pathlib
import random

import streamlit as st

_RANDOM_GENRES = [
    "pop", "rock", "hip-hop", "jazz", "electronic", "indie", "r&b",
    "soul", "funk", "reggae", "country", "classical", "lofi", "ambient",
    "folk", "blues", "metal", "latin", "dance", "alternative", "afrobeats",
]

_RANDOM_INTENT_PHRASES = [
    "random", "surprise", "anything", "any song", "any music",
    "suggest anything", "suggest something", "don't know", "no preference",
    "whatever", "doesn't matter", "don't care", "up to you",
    "something new", "discover", "no idea", "mix it up",
]


def _is_random_intent(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in _RANDOM_INTENT_PHRASES)

try:
    from .recommender import (
        extract_preferences_from_text,
        load_songs,
        recommend_songs,
        recommend_songs_from_text,
    )
    from .spotify_client import (
        SpotifyClient,
        build_search_query,
        spotify_track_to_song_dict,
    )
    from .knowledge_base import get_genre_profile
except ImportError:
    from recommender import (
        extract_preferences_from_text,
        load_songs,
        recommend_songs,
        recommend_songs_from_text,
    )
    from spotify_client import SpotifyClient, build_search_query, spotify_track_to_song_dict
    from knowledge_base import get_genre_profile


def get_recommendations(prompt: str, songs: list[dict], model: str = "gpt-4.1-mini") -> tuple[list[tuple[dict, float, str]], dict]:
    extracted = extract_preferences_from_text(prompt, model=model)

    if not extracted.is_music_request:
        return [], {
            "genre": "none", "mood": "none", "energy": "0.50",
            "energy_level": "none", "activity_context": "none",
            "acoustic_preference": "neutral", "likes_acoustic": False,
            "search_terms": "none", "extraction_source": extracted.extraction_source,
            "source": "none", "spotify_query": "", "random_mode": False,
            "error": "not_music_request",
        }

    kb_profile = get_genre_profile(extracted.genre)
    if kb_profile:
        _desc = kb_profile.get("description", "")
        kb_genre_description = _desc.split(".")[0] + "." if _desc else ""
    else:
        kb_genre_description = ""

    kb_raw_query = " ".join(p for p in [extracted.genre, extracted.mood, extracted.activity_context] if p)

    metadata = {
        "genre": extracted.genre or "none",
        "mood": extracted.mood or "none",
        "energy": f"{extracted.energy:.2f}",
        "energy_level": extracted.energy_level or "none",
        "activity_context": extracted.activity_context or "none",
        "acoustic_preference": extracted.acoustic_preference or "neutral",
        "likes_acoustic": extracted.likes_acoustic,
        "search_terms": ", ".join(extracted.search_terms) or "none",
        "extraction_source": extracted.extraction_source,
        "source": "local",
        "spotify_query": "",
        "random_mode": False,
        "kb_enriched": kb_profile is not None,
        "kb_genre_description": kb_genre_description,
        "kb_raw_query": kb_raw_query,
        "error": "",
    }

    spotify_client = SpotifyClient()
    if spotify_client.has_credentials():
        query = build_search_query(extracted)
        random_mode = not query or _is_random_intent(prompt)

        if random_mode:
            chosen = random.sample(_RANDOM_GENRES, k=2)
            query = " ".join(chosen)

        metadata["spotify_query"] = query
        metadata["random_mode"] = random_mode

        try:
            tracks = spotify_client.search_tracks(query, limit=10)
            seen = set()
            unique_tracks = []
            for track in tracks:
                key = (track.title.lower(), track.artist.lower())
                if key not in seen:
                    seen.add(key)
                    unique_tracks.append(track)

            # Convert all fetched tracks to song dicts — the full set becomes
            # the pool so skipping displayed songs doesn't exhaust it.
            all_song_dicts = [
                spotify_track_to_song_dict(track, extracted, fallback_id=index)
                for index, track in enumerate(unique_tracks, start=1)
            ]
            metadata["full_pool"] = all_song_dicts

            if metadata.get("random_mode"):
                random.shuffle(all_song_dicts)
                recommendations = [
                    (
                        song,
                        round(song["popularity"] / 100, 2),
                        "A random Spotify pick — something new to discover!",
                    )
                    for song in all_song_dicts[:5]
                ]
            else:
                recommendations = recommend_songs(
                    {
                        "genre": extracted.genre,
                        "mood": extracted.mood,
                        "energy": extracted.energy,
                        "likes_acoustic": extracted.likes_acoustic,
                    },
                    all_song_dicts,
                    k=5,
                )

            metadata["source"] = "spotify"
            # Append KB genre context to each explanation (non-random mode only)
            if not metadata["random_mode"] and kb_genre_description:
                recommendations = [
                    (song, score, f"{expl} ({kb_genre_description})")
                    for song, score, expl in recommendations
                ]
            return recommendations, metadata
        except Exception as exc:
            metadata["error"] = str(exc)

    recommendations = recommend_songs_from_text(prompt, songs, k=5)
    return recommendations, metadata


def _song_key(song: dict) -> str:
    return f"{song['title'].lower()}::{song['artist'].lower()}"


def _nudge_prefs(base_prefs: dict, liked_songs: list[dict]) -> dict:
    if not liked_songs:
        return base_prefs

    adjusted = dict(base_prefs)

    liked_energy = sum(s["energy"] for s in liked_songs) / len(liked_songs)
    adjusted["energy"] = round(0.7 * base_prefs["energy"] + 0.3 * liked_energy, 3)

    liked_genres = [s["genre"] for s in liked_songs if s.get("genre")]
    if liked_genres and len(set(liked_genres)) == 1:
        adjusted["genre"] = liked_genres[0]

    liked_acoustic = [s.get("acousticness", 0.5) for s in liked_songs]
    if sum(liked_acoustic) / len(liked_acoustic) >= 0.6:
        adjusted["likes_acoustic"] = True

    return adjusted


def _do_refresh() -> None:
    fb = st.session_state.feedback
    pool = st.session_state.songs_pool

    liked = [s for s, _, _ in st.session_state.current_recs
             if fb.get(_song_key(s)) == "like"]
    excluded_keys = {k for k, v in fb.items() if v in ("dislike", "skip")}

    filtered_pool = [s for s in pool if _song_key(s) not in excluded_keys]
    if not filtered_pool:
        return

    # Shrink the pool permanently so songs excluded in this cycle
    # don't reappear in future refreshes after feedback is reset.
    st.session_state.songs_pool = filtered_pool

    adjusted_prefs = _nudge_prefs(st.session_state.base_prefs, liked)
    new_recs = recommend_songs(adjusted_prefs, filtered_pool, k=5)

    st.session_state.current_recs = new_recs
    st.session_state.feedback = {}


st.set_page_config(page_title="MoodMatch", page_icon="♪", layout="wide")

if "current_recs" not in st.session_state:
    st.session_state.current_recs = []
if "songs_pool" not in st.session_state:
    st.session_state.songs_pool = []
if "pool_source" not in st.session_state:
    st.session_state.pool_source = "local"
if "base_prefs" not in st.session_state:
    st.session_state.base_prefs = {}
if "feedback" not in st.session_state:
    st.session_state.feedback = {}
if "metadata" not in st.session_state:
    st.session_state.metadata = {}

_DATA_PATH = pathlib.Path(__file__).parent.parent / "data" / "songs.csv"
songs = load_songs(str(_DATA_PATH))

st.title("MoodMatch Music Recommender")
st.caption("Describe the music you want, and the app will extract preferences, search for tracks, and explain each match.")

with st.sidebar:
    st.subheader("OpenAI Model")
    selected_model = st.selectbox(
        "Preference extraction model",
        options=["gpt-4.1-mini", "gpt-4.1", "gpt-4.1-nano", "gpt-4o-mini", "gpt-4o"],
        index=0,
    )

    st.subheader("Data Source")
    spotify_ready = SpotifyClient().has_credentials()
    st.write("Spotify credentials detected:" if spotify_ready else "Spotify credentials detected: not set")
    if not spotify_ready:
        st.caption("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in your environment to enable Spotify search.")

prompt = st.text_area(
    "What do you want to listen to?",
    placeholder="Example: I want chill lofi music for studying with a soft acoustic feel.",
    height=120,
)

submitted = st.button("Find Songs", use_container_width=True)

if submitted:
    if not prompt.strip():
        st.warning("Enter a music request first.")
    else:
        with st.spinner("Building recommendations..."):
            recommendations, metadata = get_recommendations(prompt.strip(), songs, model=selected_model)

        if metadata.get("error") == "not_music_request":
            st.warning(
                "This app is for music recommendations only. "
                "Try something like: *'chill lofi for studying'* or *'surprise me with something upbeat'*."
            )
        else:
            st.session_state.current_recs = recommendations
            st.session_state.metadata = metadata
            st.session_state.feedback = {}

            if metadata["source"] == "spotify":
                st.session_state.songs_pool = metadata["full_pool"]
                st.session_state.pool_source = "spotify"
            else:
                st.session_state.songs_pool = songs
                st.session_state.pool_source = "local"

            st.session_state.base_prefs = {
                "genre": metadata["genre"] if metadata["genre"] != "none" else "",
                "mood": metadata["mood"] if metadata["mood"] != "none" else "",
                "energy": float(metadata["energy"]),
                "likes_acoustic": metadata["likes_acoustic"],
            }

            pref_col, source_col = st.columns([2, 1])
            with pref_col:
                st.subheader("Extracted Preferences")
                st.write(f"Genre: {metadata['genre']}")
                st.write(f"Mood: {metadata['mood']}")
                st.write(f"Energy: {metadata['energy']}")
                st.write(f"Energy level: {metadata['energy_level']}")
                st.write(f"Activity: {metadata['activity_context']}")
                st.write(f"Acoustic preference: {metadata['acoustic_preference']}")
                st.write(f"Likes acoustic: {metadata['likes_acoustic']}")
                st.write(f"Search terms: {metadata['search_terms']}")
            with source_col:
                st.subheader("Source")
                st.write(f"Using: {metadata['source']}")
                if metadata.get("random_mode"):
                    st.caption("No music signals detected — showing random Spotify picks.")
                st.write(f"Preference extraction: {metadata['extraction_source']}")
                if metadata["extraction_source"] == "openai":
                    st.write(f"Model: {selected_model}")
                if metadata["spotify_query"] and not metadata.get("random_mode"):
                    if metadata.get("kb_enriched"):
                        st.write(f"Query (without KB): `{metadata['kb_raw_query']}`")
                        st.write(f"Query (with KB): `{metadata['spotify_query']}`")
                    else:
                        st.write(f"Spotify query: {metadata['spotify_query']}")
                if metadata.get("kb_enriched") and metadata.get("kb_genre_description"):
                    st.caption(f"KB: {metadata['kb_genre_description']}")

            if metadata["error"]:
                st.info(f"Spotify search failed, so local catalog fallback was used: {metadata['error']}")

if st.session_state.current_recs:
    if st.session_state.feedback:
        liked_n = sum(1 for v in st.session_state.feedback.values() if v == "like")
        disliked_n = sum(1 for v in st.session_state.feedback.values() if v == "dislike")
        st.caption(f"Feedback: {liked_n} liked · {disliked_n} disliked")
        st.button("🔄 Refresh Recommendations", on_click=_do_refresh, use_container_width=True)

    st.subheader("Recommendations")
    if not st.session_state.current_recs:
        st.warning("No recommendations found.")
    else:
        for index, (song, score, explanation) in enumerate(st.session_state.current_recs, start=1):
            key = _song_key(song)
            current_fb = st.session_state.feedback.get(key, "")
            with st.container():
                st.markdown(f"**{index}. {song['title']}** by {song['artist']}")
                st.write(f"Score: {score:.2f}")
                st.write(f"Why it fits: {explanation}")
                if song.get("album"):
                    st.write(f"Album: {song['album']}")
                if song.get("spotify_url"):
                    st.markdown(f"[Open in Spotify]({song['spotify_url']})")

                col1, col2, col3, _ = st.columns([1, 1, 1, 5])
                with col1:
                    lbl = "✅ Liked" if current_fb == "like" else "👍 Like"
                    if st.button(lbl, key=f"like_{key}_{index}"):
                        st.session_state.feedback[key] = "like"
                        st.rerun()
                with col2:
                    lbl = "❌ Disliked" if current_fb == "dislike" else "👎 Dislike"
                    if st.button(lbl, key=f"dislike_{key}_{index}"):
                        st.session_state.feedback[key] = "dislike"
                        st.rerun()
                with col3:
                    lbl = "⏭ Skipped" if current_fb == "skip" else "⏭ Skip"
                    if st.button(lbl, key=f"skip_{key}_{index}"):
                        st.session_state.feedback[key] = "skip"
                        st.rerun()
                st.divider()
