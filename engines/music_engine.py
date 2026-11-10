import os
import re
import time
import html
import requests

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

# Fjalët që hiqen nga fillimi i komandës zanore para kërkimit
FILLER_PATTERN = re.compile(
    r"^\s*(please\s+)?(play|put on|listen to|luaj|luaje|vendos|ndiz|ndize|dua te degjoj|dua të dëgjoj)\s+",
    re.IGNORECASE,
)

CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 orë, kursen kuotën e API-t


class MusicEngine:
    def __init__(self):
        self.api_key = os.environ.get("YOUTUBE_API_KEY", "")
        self._cache = {}  # {query_normalizuar: (timestamp, rezultati)}

    # ---------- Pika hyrëse ----------
    def process(self, query: str) -> dict:
        return self.search_music(query)

    # ---------- Logjika kryesore ----------
    def search_music(self, query: str) -> dict:
        query = self._clean_query(query)
        if not query:
            return {"error": "No search query provided"}

        if not self.api_key:
            print("[FalconAI Music Engine] Mungon YOUTUBE_API_KEY")
            return {"error": "Music service is not configured"}

        cache_key = query.lower()
        cached = self._cache.get(cache_key)
        if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
            print(f"[FalconAI Music Engine] Cache hit: {query}")
            return cached[1]

        print(f"[FalconAI Music Engine] Kërkimi për: {query}")

        try:
            candidates = self._search(query)
            if not candidates:
                return {"error": "No results found"}

            video = self._pick_playable(candidates)
            if not video:
                return {"error": "No playable result found for this song"}

            title = html.unescape(video["title"])
            result = {
                "text": f"Playing {title}",
                "voice_text": f"Now playing {title}",
                "data": {
                    "title": title,
                    "video_id": video["id"],
                },
            }
            self._cache[cache_key] = (time.time(), result)
            print(f"[FalconAI Music Engine] U gjet: {title} ({video['id']})")
            return result

        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            body = e.response.text[:300] if e.response is not None else ""
            print(f"[FalconAI Music Engine Gabim] HTTP {status}: {body}")
            if status == 403:
                return {"error": "Music search quota reached, try again later"}
            return {"error": "Music search failed"}
        except requests.RequestException as e:
            print(f"[FalconAI Music Engine Gabim] Rrjeti: {e}")
            return {"error": "Music service unreachable"}
        except Exception as e:
            print(f"[FalconAI Music Engine Gabim]: {e}")
            return {"error": str(e)}

    # ---------- Ndihmëse ----------
    @staticmethod
    def _clean_query(query: str) -> str:
        if not query:
            return ""
        # Android mund të dërgojë "play play ...", ndaj pastrohet disa herë
        for _ in range(3):
            cleaned = FILLER_PATTERN.sub("", query).strip()
            if cleaned == query:
                break
            query = cleaned
        # Hiq pikësimin e tepërt nga transkriptimi i zërit
        query = re.sub(r"[\"“”]", "", query).strip(" .,!?")
        return query

    def _search(self, query: str) -> list:
        """Kthen deri në 10 kandidatë (id + titull) nga YouTube Search."""
        # Shtojmë "audio" në kërkesë për të shmangur bllokimet e embed (Error 152)
        safe_query = f"{query} audio"
        
        r = requests.get(
            YOUTUBE_SEARCH_URL,
            params={
                "part": "snippet",
                "q": safe_query,
                "type": "video",
                "videoCategoryId": "10",    # Music
                "videoEmbeddable": "true",    # vetëm video që lejojnë embed
                "maxResults": 10,
                "key": self.api_key,
            },
            timeout=10,
        )
        r.raise_for_status()
        items = r.json().get("items", [])
        return [
            {"id": it["id"]["videoId"], "title": it["snippet"]["title"]}
            for it in items
            if it.get("id", {}).get("videoId")
        ]

    def _pick_playable(self, candidates: list):
        """Kontrollon me videos.list dhe kthen të parin që luhet."""
        ids = ",".join(c["id"] for c in candidates)
        r = requests.get(
            YOUTUBE_VIDEOS_URL,
            params={
                "part": "status,contentDetails",
                "id": ids,
                "key": self.api_key,
            },
            timeout=10,
        )
        r.raise_for_status()
        info = {v["id"]: v for v in r.json().get("items", [])}

        for c in candidates:  # ruan rendin e rëndësisë nga kërkimi
            v = info.get(c["id"])
            if not v:
                continue
            if not v.get("status", {}).get("embeddable", False):
                continue
            if v.get("status", {}).get("privacyStatus") != "public":
                continue
            return c
        return None
