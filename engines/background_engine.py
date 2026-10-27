import os
import re
import json
import logging
import urllib.request
import urllib.parse
import urllib.error

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("FalconAI.BackgroundEngine")

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "EbzpmWRrq890O46TEN7Gk0orPl19Cs6cCOrX61hqMtI")
UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"
UNSPLASH_TIMEOUT = 8

_model = None

def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("[BACKGROUND] Loading local embedding model (first call only)...")
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            logger.error(
                "[BACKGROUND] sentence-transformers not installed. "
                "Run: pip install sentence-transformers --break-system-packages"
            )
            raise
    return _model


_TRIGGER_WORDS = {
    "change", "set", "make", "switch", "update", "background", "backgrounds",
    "wallpaper", "the", "to", "my", "screen", "home", "please", "can", "you",
    "i", "want", "would", "like", "with", "a", "an",
    "dua", "me", "ta", "beje", "bëje", "sfond", "sfondin", "backgroundin",
    "ndrysho", "ndryshoje", "vendos", "vendose", "ekranin", "shtepine",
    "shtëpinë", "je", "lutem", "dhe", "edhe", "and", "of",
}

_AL_TO_EN = {
    "univers": "universe", "hapesire": "space", "hapësirë": "space",
    "det": "ocean", "male": "mountains", "mal": "mountain",
    "pyll": "forest", "qytet": "city", "natyre": "nature", "natyrë": "nature",
    "diell": "sun", "hene": "moon", "hënë": "moon", "yje": "stars",
    "shi": "rain", "dëborë": "snow", "debore": "snow", "plazh": "beach",
    "liqen": "lake", "lule": "flowers", "vjeshte": "autumn", "vjeshtë": "autumn",
    "dimer": "winter", "dimër": "winter", "vere": "summer", "verë": "summer",
    "pranvere": "spring", "pranverë": "spring", "natë": "night", "nate": "night",
    "zjarr": "fire", "uje": "water", "ujë": "water", "shkretetire": "desert",
    "shkretëtirë": "desert", "galaktike": "galaxy", "galaktikë": "galaxy",
}


def extract_background_topic(query: str) -> str:
    words = re.findall(r"[a-zA-ZëçÇË]+", query.lower())
    subject_words = [w for w in words if w not in _TRIGGER_WORDS]

    if not subject_words:
        return query.strip()

    translated = [_AL_TO_EN.get(w, w) for w in subject_words]
    return " ".join(translated)

def _search_unsplash_api(topic: str, per_page: int = 10, timeout: int = UNSPLASH_TIMEOUT):
    if not UNSPLASH_ACCESS_KEY:
        logger.warning(
            "[BACKGROUND] UNSPLASH_ACCESS_KEY is not set. "
            "Get a free key at https://unsplash.com/developers"
        )
        return []

    params = urllib.parse.urlencode({
        "query": topic,
        "per_page": per_page,
        "orientation": "landscape",
    })
    url = f"{UNSPLASH_SEARCH_URL}?{params}"

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
            "Accept-Version": "v1",
            "User-Agent": "FalconAI/3.0 (+https://www.falconai-tv.com)",
        },
        method="GET",
    )

    candidates = []
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))

        for photo in data.get("results", []):
            image_url = photo.get("urls", {}).get("regular", "")
            if not image_url:
                continue

            alt_desc = photo.get("alt_description") or photo.get("description") or ""
            page_url = photo.get("links", {}).get("html", "")

            candidates.append({
                "image_url": image_url,
                "description": alt_desc,
                "page_url": page_url,
            })

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        logger.error(f"[BACKGROUND] Unsplash API error {e.code}: {error_body}")
    except urllib.error.URLError as e:
        logger.error(f"[BACKGROUND] Could not reach Unsplash API: {e}")
    except Exception as e:
        logger.error(f"[BACKGROUND] Unexpected error querying Unsplash: {e}")

    return candidates

class BackgroundEngine:
    def __init__(self):
        pass

    def search(self, voice_query: str, top_k: int = 5):
        if not voice_query or not voice_query.strip():
            return {"query": voice_query, "results": []}

        topic = extract_background_topic(voice_query)
        logger.info(f"[BACKGROUND] '{voice_query}' -> topic: '{topic}'")

        candidates = _search_unsplash_api(topic)

        if not candidates:
            note = (
                "UNSPLASH_ACCESS_KEY is missing — get a free key at "
                "https://unsplash.com/developers"
                if not UNSPLASH_ACCESS_KEY
                else "No matching photos found on Unsplash for this topic."
            )
            return {
                "query": voice_query,
                "topic_used": topic,
                "results": [],
                "note": note,
            }

        model = _get_model()
        query_vec = model.encode([voice_query], normalize_embeddings=True)[0]

        corpus_texts = [
            c["description"] if c["description"] else topic for c in candidates
        ]
        candidate_vecs = model.encode(corpus_texts, normalize_embeddings=True)
        sims = candidate_vecs @ query_vec

        ranked = sorted(zip(candidates, sims), key=lambda pair: pair[1], reverse=True)

        results = []
        for cand, score in ranked[:top_k]:
            results.append({
                "image_url": cand["image_url"],
                "description": cand["description"],
                "page_url": cand["page_url"],
                "match_score": round(float(score), 3),
            })

        return {
            "query": voice_query,
            "topic_used": topic,
            "best_match": results[0] if results else None,
            "results": results,
        }


if __name__ == "__main__":
    engine = BackgroundEngine()
    for test_query in [
        "dua me univers backgroundin",
        "change background to a rainy tokyo street at night",
    ]:
        print(f"\n=== Query: {test_query} ===")
        print(json.dumps(engine.search(test_query, top_k=3), indent=2))