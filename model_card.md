# Model Card: MoodMatch Music Recommender

---

## 1. Model Name

**MoodMatch 1.0**
*(Extended from VibeFinder 1.0 — the original CLI-based content-filtering prototype)*

---

## 2. Intended Use

MoodMatch is a natural-language music recommendation system. A user describes what they want to hear — a genre, a mood, an activity, or just "surprise me" — and the system returns five ranked song recommendations with an explanation for each match.

**Who it is for:** Anyone who wants personalized music suggestions without needing to know the right search terms. The primary demo context is a course project, but the architecture mirrors real production patterns used in commercial music platforms.

**What it assumes about the user:**
- The user communicates in English.
- The user describes a listening intent, not a specific song title or artist name.
- The user may give vague input ("something chill") or structured input ("high energy rock for working out") — both are handled.

**What it is not for:**
- Artist or album lookups.
- Lyric search or song identification.
- Personalized recommendations based on listening history (no user account required or supported).

---

## 3. How the Model Works

MoodMatch has two main stages: understanding what the user wants, and finding songs that match.

### Stage 1 — Understanding the Request

When a user types a prompt, the system sends it to OpenAI's language model (GPT-4.1-mini by default). The model reads the prompt and extracts structured signals: what genre the user seems to want, what mood they are in, how energetic the music should feel, what activity they are doing (studying, working out, driving, etc.), and whether they prefer acoustic or produced sounds.

The model also sets a guardrail flag that detects if the input is not a music request at all — for example, if someone asks for a recipe or a coding tip. Those requests are blocked before any search is performed.

If no OpenAI key is available, the system falls back to keyword matching: it scans the prompt for known genre and mood words and infers energy from activity-related terms like "workout" or "sleep."

### Stage 2 — Finding and Ranking Songs

Once preferences are extracted, the system searches Spotify for up to ten tracks matching those signals. This is the RAG (Retrieval-Augmented Generation) step — the system retrieves real, current music from an external source rather than relying on a fixed internal list.

Each retrieved track is then scored against the user's preferences using five weighted factors:

| Factor | Weight | How it is scored |
|---|---|---|
| Genre match | 20% | 1.0 if the track's genre matches, 0.0 otherwise |
| Mood match | 20% | 1.0 if the mood matches, 0.0 otherwise |
| Energy match | 35% | Closeness between user's target energy and track energy (0–1 scale) |
| Acoustic preference | 10% | Higher score if the track's acousticness aligns with user preference |
| Popularity | 15% | Track's Spotify popularity score normalized to 0–1 |

Tracks are sorted by total score and the top five are returned. Each result includes a plain-English explanation of why it ranked where it did.

### Feedback Loop

After seeing results, the user can mark individual tracks as Liked, Disliked, or Skipped. Clicking "Refresh Recommendations" removes disliked tracks from the pool and nudges the user's energy preference 30% toward the energy of liked tracks, then re-runs the scorer. This allows results to improve within a session without requiring any login or persistent account.

### Random Mode

If the prompt contains no music signals (no genre, mood, or activity), or includes randomness-intent phrases like "surprise me" or "anything goes," the system picks two genres at random from a 20-genre pool, fetches tracks from Spotify, shuffles the results, and returns them as a discovery set rather than a preference-matched ranking.

---

## 4. Data

### Primary Source — Spotify Web API (live)

When Spotify credentials are configured, MoodMatch retrieves up to ten tracks per query from Spotify's search index. Each track provides a title, artist, album, Spotify URL, and popularity score. Spotify's audio features endpoint (which would provide danceability, valence, and precise tempo per track) requires user-level OAuth authorization, which is beyond the Client Credentials flow used here — so those fields are approximated from the extracted preferences.

**Coverage:** Effectively the entire Spotify catalog — tens of millions of tracks across all genres and eras.

### Fallback Source — Local CSV Catalog

When Spotify is unavailable, the system falls back to `data/songs.csv`: a hand-curated 20-song dataset with full audio feature annotations.

| Property | Details |
|---|---|
| Total songs | 20 |
| Genres | pop, rock, lofi, classical, electronic, folk, hip-hop, reggae, ambient, acoustic, indie pop, country |
| Moods | happy, chill, intense, peaceful, moody, romantic, focused |
| Features per song | id, title, artist, genre, mood, energy, tempo\_bpm, valence, danceability, acousticness |

**Gaps in the local catalog:** The 20-song set is narrow by design. Jazz, synthwave, R&B, metal, and most non-English music are absent or underrepresented. Results from the local catalog reflect this limited scope.

---

## 5. Strengths

- **Natural language input** works well for common patterns: activity-based requests ("studying," "workout," "road trip"), mood-based requests ("something happy," "melancholy indie"), and genre-based requests ("lofi," "classical," "hip-hop").

- **Transparent explanations** make each recommendation legible. The user knows exactly which features drove the ranking — not just a score, but a sentence that reads like a human recommendation.

- **Graceful degradation** means the app is functional at every level of API access: full Spotify + OpenAI, Spotify only, OpenAI only, or completely offline against the local CSV.

- **Random mode** handles vague or open-ended prompts without returning nonsensical results. Users who want discovery rather than precision get a genuinely shuffled set.

- **Guardrails** keep the system on-task without requiring a separate moderation API call — the validation is embedded in the same extraction call.

---

## 6. Limitations and Bias

**Spotify audio features are approximated.** Because Spotify's per-track audio feature API requires user-level authorization, energy, danceability, valence, and acousticness are assigned from the extracted preferences — not from the actual track. This means every Spotify result in a given query gets the same energy and acousticness score, and the scorer can only differentiate them by genre, mood match, and popularity. Popularity becomes the main tiebreaker in Spotify mode.

**Popularity as a proxy for quality.** Tracks with higher Spotify popularity consistently score above lesser-known equivalents, even when those equivalents might be a better stylistic match. This biases results toward mainstream, widely-known music and can make it harder for niche or independent artists to surface.

**Genre and mood are binary.** Genre match scores 1.0 or 0.0 — there is no partial credit for related genres (e.g., "lofi" and "ambient" share qualities but score as complete mismatches). A more nuanced genre embedding would improve cross-genre recommendations.

**Keyword fallback is coarse.** Without an OpenAI key, the system only recognizes explicitly named genres and moods. Synonyms, metaphors, and indirect descriptions ("something for a rainy day") produce empty preferences and trigger random mode rather than a meaningful search.

**Session-only feedback.** Liked and disliked signals are held in browser session state and reset when the user submits a new prompt or refreshes the page. The system cannot learn a user's taste over time.

**English-only.** Both the OpenAI prompt and the keyword fallback patterns are English-only. Non-English music requests will produce poor extractions.

---

## 7. Evaluation

### Automated Tests — 14 pytest tests

| Test | What it verifies |
|---|---|
| `test_recommend_returns_songs_sorted_by_score` | Top result has the highest score and correct genre/mood |
| `test_explain_recommendation_returns_non_empty_string` | Explanations are never blank |
| `test_extract_preferences_from_happy_pop_text` | Keyword extraction correctly identifies pop + happy |
| `test_extract_preferences_from_chill_study_text` | Correctly sets lofi genre, chill mood, energy 0.4, activity studying |
| `test_extract_preferences_falls_back_to_defaults` | Vague input returns safe defaults, not errors |
| `test_extract_preferences_from_high_energy_workout_text` | Energy 0.9 and workout activity correctly inferred |
| `test_extract_preferences_openai_unavailable_falls_back_without_crashing` | Graceful keyword fallback when OpenAI client is None |
| `test_extract_preferences_uses_openai_structured_payload` | Mock OpenAI client returns rock/intense/high correctly parsed |
| `test_recommend_songs_from_text_returns_explanations` | End-to-end: text input → ranked results with non-empty explanations |
| Spotify: auth, search, normalization, query building | Spotify client handles tokens, HTTP responses, and deduplication |

### Manual Testing

Four CLI profiles from the original VibeFinder prototype were re-validated: Happy Pop Fan, Intense Rock Fan, Chill Lofi Fan, and Peaceful Classical Fan. In each case the top result matched the expected genre and mood, and the explanation text correctly cited the matching features.

**What surprised me:** After switching to Spotify mode, all five results initially received identical scores (0.85) with identical explanations. Investigation revealed that every Spotify track was being assigned the same energy and acousticness from the extracted preferences — so the scorer had no per-track signal to differentiate them beyond popularity. Increasing the popularity weight from 10% to 15% and decreasing energy from 40% to 35% created visible score spread, but the root issue (audio features not available per-track without user OAuth) remains a structural limitation.

**Duplicate results:** Spotify returned the same song from multiple album editions (e.g., an original album and a greatest-hits compilation). Deduplication on `(title.lower(), artist.lower())` before ranking resolved this.

---

## 8. Future Work

**Per-track audio features.** The most impactful improvement would be obtaining real energy, danceability, and valence per track. This could be done via user-level Spotify OAuth, or by integrating a different audio feature API. Without this, the Spotify scorer is mainly distinguishing tracks by popularity.

**Persistent feedback.** Storing liked and disliked signals between sessions (even in a lightweight local file or browser `localStorage`) would allow the nudge algorithm to improve over time rather than resetting on every new query.

**Embedding-based genre similarity.** Replacing the binary genre match with cosine similarity over genre embeddings would allow partial credit for related genres, improving results for cross-genre requests.

**Multi-turn conversation.** Letting users refine a request through follow-up messages ("make it more acoustic," "something a bit slower") rather than submitting a single prompt each time would feel more natural.

**Evaluation metrics.** Precision@k and normalized discounted cumulative gain (NDCG) against a labeled test set would replace manual spot-checking as the catalog grows.

---

## 9. Personal Reflection

Building MoodMatch taught me that the gap between a working prototype and a reliable AI system is mostly about failure modes — not the happy path. The scoring logic was straightforward to write. What took real effort was understanding why OpenAI extraction silently failed (wrong API method), why Spotify returned duplicates (multiple album editions), and why all results scored identically (audio features weren't per-track). Each of those bugs was invisible until I looked carefully at the data flowing between components.

The guardrail feature shifted how I think about prompt design. A user typing "give me something random" caused the app to search for songs literally called "Random" — not because the AI was wrong, but because no one told it that search terms should be music signals, not filler words. Constraints on what the model should output matter as much as what it should understand.

Most importantly, this project made RAG concrete. The phrase "retrieval-augmented generation" sounds abstract until you build the pipeline yourself and realize: the model doesn't know what's on Spotify today, and you can't make it know — you have to go get that information and bring it to the model. Once I understood that, a lot of other AI system patterns clicked into place.
