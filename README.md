# MoodMatch — Natural-Language Music Recommender

> Built on top of **VibeFinder CLI**, a content-based music recommender that ranked songs from a local CSV catalog using genre, mood, and energy preferences. VibeFinder established the core scoring and explanation logic, and tested the idea that a small set of audio features could produce meaningful, explainable recommendations. MoodMatch extends that foundation into a full AI-powered application with natural-language input, live Spotify search, and an interactive feedback loop.

---

## What It Does and Why It Matters

MoodMatch lets a user describe what they want to hear in plain English — *"chill lofi beats for studying"* or *"surprise me with something upbeat"* — and returns five ranked song recommendations with explanations for each match. It demonstrates a complete AI pipeline: natural-language understanding, external data retrieval, intelligent ranking, and user feedback that improves future results.

The project shows how the core techniques behind commercial music platforms (preference modeling, retrieval-augmented generation, iterative refinement) can be implemented with accessible tools and a small codebase.

---

## Architecture Overview

```
User Prompt (natural language)
        │
        ▼
┌─────────────────────┐
│  Preference         │  OpenAI (gpt-4.1-mini) extracts genre, mood,
│  Extractor          │  energy, activity context, acoustic preference,
│                     │  and is_music_request guardrail flag.
│  Keyword fallback   │  If no API key, regex-style keyword matching.
└────────┬────────────┘
         │ ExtractedPreferences
         ▼
┌─────────────────────┐
│  Guardrail Check    │  Blocks non-music requests (recipes, code help,
│                     │  math, etc.) before hitting any external API.
└────────┬────────────┘
         │ valid request
         ▼
┌─────────────────────┐        ┌──────────────────────┐
│  Spotify Search     │        │  Local CSV Catalog   │
│  (RAG retrieval)    │──────▶ │  Fallback (20 songs) │
│                     │  fail  └──────────────────────┘
│  Client Credentials │
│  OAuth → Search API │
└────────┬────────────┘
         │ up to 10 tracks
         ▼
┌─────────────────────┐
│  Recommender        │  Weighted scoring:
│  Scorer             │  genre 20% · mood 20% · energy 35%
│                     │  acousticness 10% · popularity 15%
└────────┬────────────┘
         │ ranked (song, score, explanation)
         ▼
┌─────────────────────┐
│  Streamlit UI       │  Displays results with 👍 Like / 👎 Dislike /
│  + Feedback Loop    │  ⏭ Skip buttons. "Refresh" re-ranks with
│                     │  adjusted preferences based on feedback.
└─────────────────────┘
```

The Spotify integration is the **RAG** component: the system retrieves real tracks from an external source before generating its ranked, explained response — rather than answering from a fixed internal catalog alone.

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- A [Spotify Developer](https://developer.spotify.com/dashboard) account (free) for live search
- An OpenAI API key (optional — the app works without one using keyword extraction)

### 1. Clone and install dependencies

```bash
git clone <your-repo-url>
cd Applied_AI_final_Project_Codepath.git
pip install -r requirements.txt
```

### 2. Set environment variables

Create a `.env` file in the project root, or export variables in your shell:

```bash
# Required for live Spotify search
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here

# Optional — enables OpenAI preference extraction
OPENAI_API_KEY=your_openai_key_here
```

> Without Spotify credentials the app falls back to the local 20-song CSV catalog.
> Without an OpenAI key it uses keyword matching for preference extraction.

### 3. Run the Streamlit app

```bash
streamlit run src/app.py
```

Open `http://localhost:8501` in your browser.

### 4. (Optional) Run the CLI version

```bash
python -m src.main
```

### 5. Run the test suite

```bash
pytest -v
```

Expected output: **14 tests pass**.

---

## Sample Interactions

### Example 1 — Specific genre and activity

**Input:**
> "I want chill lofi music for studying"

**Extracted preferences:**
- Genre: `lofi` · Mood: `chill` · Energy: `0.40` · Activity: `studying`

**Top result:**
> **Midnight Coding** by LoRoom
> Score: 0.87
> *"This track fits because it suits your studying session, matches the lofi genre you requested, carries the chill mood you're looking for, and closely matches your energy level."*

---

### Example 2 — Random / no specific preference

**Input:**
> "Surprise me with something"

**Behaviour:** No music signals detected → random mode activates. Two genres are picked randomly from a 20-genre pool, Spotify is searched, results are shuffled.

**Sample result:**
> **Blinding Lights** by The Weeknd
> Score: 0.87 (popularity-based)
> *"A random Spotify pick — something new to discover!"*

Each run returns a different shuffle of genres and tracks.

---

### Example 3 — Off-topic guardrail

**Input:**
> "Can you write me a Python script to sort a list?"

**Behaviour:** OpenAI sets `is_music_request: false`. No Spotify call is made.

**UI response:**
> ⚠️ *"This app is for music recommendations only. Try something like: 'chill lofi for studying' or 'surprise me with something upbeat'."*

---

### Example 4 — Feedback loop

**Input:**
> "High energy rock songs for working out"

**Flow:**
1. Five rock tracks returned, scored by energy match and popularity.
2. User clicks 👎 Dislike on two tracks with heavy metal vibes.
3. User clicks 👍 Like on a track with high danceability.
4. User clicks **🔄 Refresh Recommendations**.
5. Disliked tracks are excluded; `target_energy` nudges 30% toward the liked track's energy; new top-5 returned.

---

## Design Decisions and Trade-offs

| Decision | Why | Trade-off |
|---|---|---|
| OpenAI for preference extraction | Natural language is too varied for reliable regex alone; structured JSON output via `response_format` gives consistent, typed fields | Adds API cost and latency; keyword fallback ensures the app still works without a key |
| Spotify Client Credentials (not user OAuth) | Zero friction — no login, no user scope required | Can't access personalized user data like listening history or saved tracks |
| RAG over pure generation | Grounds recommendations in real, current Spotify catalog instead of the model's training data | Adds network dependency; falls back to local CSV if Spotify is unavailable |
| Weighted scoring (not ML model) | Transparent, explainable, easy to tune; explanations map directly to score components | Static weights don't adapt to individual users over time |
| Session-only feedback | Simple; no database or auth needed for a demo | Feedback resets on page refresh; can't learn across sessions |
| `is_music_request` in extraction schema | Single API call doubles as guardrail; no extra latency | Only works when OpenAI key is present; keyword blocklist is the fallback |
| Random mode via genre sampling | Spotify has no "random" endpoint; sampling from a genre pool + shuffling gives genuine variety | Results still reflect genre popularity biases in Spotify's index |

---

## Testing Summary

**14 tests across two modules** (`tests/test_recommender.py`, `tests/test_spotify_client.py`).

### What is tested

| Area | Tests |
|---|---|
| Recommendation scoring and sort order | `test_recommend_returns_songs_sorted_by_score` |
| Explanation generation | `test_explain_recommendation_returns_non_empty_string` |
| Keyword preference extraction | 3 tests covering happy/pop, chill/lofi/studying, and high-energy workout |
| Default fallback values | `test_extract_preferences_falls_back_to_defaults` |
| OpenAI extraction with mock client | `test_extract_preferences_uses_openai_structured_payload` |
| OpenAI unavailable → keyword fallback | `test_extract_preferences_openai_unavailable_falls_back_without_crashing` |
| End-to-end text-to-recommendations | `test_recommend_songs_from_text_returns_explanations` |
| Spotify auth, search, normalization | 4 tests in `test_spotify_client.py` |

### What worked

- The mock-based OpenAI test proved the Chat Completions integration was correct before any live API calls.
- Keyword fallback tests gave confidence that the app degrades gracefully when no API key is present.
- Running `pytest -v` after every change caught regressions immediately — for example, when the scoring weights were adjusted, the sort-order test confirmed the top song still scored highest.

### What didn't work initially

- The original code used the **Responses API** (`client.responses.create`) for OpenAI calls. The schema shape was wrong for that API, so extraction silently failed and fell back to keywords every time. Switching to **Chat Completions** (`client.chat.completions.create`) with `response_format` fixed it.
- Spotify was returning the same song from multiple albums (e.g., "Could You Be Loved" on both its original album and a greatest-hits compilation). Deduplication on `(title.lower(), artist.lower())` resolved the duplicate results.

### What I learned

Testing the AI components with mocks (injecting a fake OpenAI client that returns controlled JSON) is essential. It makes the extraction logic independently verifiable without API costs or network flakiness, and it forces you to define exactly what the AI contract should return.

---

## Reflection

### What this project taught me about AI

Building MoodMatch made abstract AI concepts concrete. Retrieval-Augmented Generation stopped being a buzzword and became an obvious solution to a real problem: the model doesn't know what's on Spotify today, so you have to retrieve that data first. Structured output (forcing the model to return valid JSON with a defined schema) was the difference between a reliable pipeline and one that broke silently.

The guardrail feature was a lesson in how easily language models can be pulled off-task. A user typing "give me something random" causes the system to search Spotify for songs literally titled "Random" or "Ransom" — not because the model misunderstood, but because no one told it that search terms should be music signals, not filler words. Careful prompt design and schema constraints fixed that.

### What this project taught me about problem-solving

The feedback loop (like/dislike/refresh) was the most architecturally interesting feature. The first instinct was to store liked songs in a database. The second instinct was to add new fields to the scoring model. The right answer was much simpler: adjust the `target_energy` and `favorite_genre` values already used by the existing scorer, and filter the disliked songs from the pool. No new database, no new model — just better use of what was already there.

That pattern — solve the problem with what you already have before adding new machinery — is one I'll carry forward.

---

## Project Structure

```
.
├── src/
│   ├── app.py              # Streamlit UI, feedback loop, guardrail wiring
│   ├── recommender.py      # Scoring, explanation, preference extraction
│   ├── spotify_client.py   # Spotify auth, search, data normalization
│   └── main.py             # CLI runner
├── tests/
│   ├── test_recommender.py # 9 recommender tests
│   └── test_spotify_client.py  # 5 Spotify client tests
├── data/
│   └── songs.csv           # Local 20-song fallback catalog
└── requirements.txt
```

---

## Tech Stack

- **Python 3.10+**
- **Streamlit** — UI framework
- **OpenAI Python SDK** — preference extraction via `gpt-4.1-mini`
- **Spotify Web API** — live track search (Client Credentials flow)
- **pytest** — test suite
- **requests** — Spotify HTTP calls
