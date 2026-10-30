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

def _search_unsplash_api(topic: str, per_page: int = 1, timeout: int = UNSPLASH_TIMEOUT):
    if not UNSPLASH_ACCESS_KEY:
        logger.warning("[BACKGROUND] UNSPLASH_ACCESS_KEY is not set.")
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

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))

        results = data.get("results", [])
        if results:
            photo = results[0]
            image_url = photo.get("urls", {}).get("regular", "")
            alt_desc = photo.get("alt_description") or photo.get("description") or ""
            page_url = photo.get("links", {}).get("html", "")
            
            return {
                "image_url": image_url,
                "description": alt_desc,
                "page_url": page_url
            }
    except Exception as e:
        logger.error(f"[BACKGROUND] Error querying Unsplash: {e}")

    return None

class BackgroundEngine:
    def __init__(self):
        pass

    def search(self, voice_query: str, top_k: int = 1):
        if not voice_query or not voice_query.strip():
            return {"query": voice_query, "results": []}

        topic = extract_background_topic(voice_query)
        logger.info(f"[BACKGROUND] '{voice_query}' -> topic: '{topic}'")

        best_match = _search_unsplash_api(topic)

        return {
            "query": voice_query,
            "topic_used": topic,
            "best_match": best_match,
            "results": [best_match] if best_match else []
        }


if __name__ == "__main__":
    engine = BackgroundEngine()
    print(json.dumps(engine.search("rainy tokyo street"), indent=2))
