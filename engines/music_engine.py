import os
import re
import html
import requests

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

FILLER_PATTERN = re.compile(
    r"^\s*(please\s+)?(play|put on|listen to|luaj|luaje|vendos|ndiz|ndize|dua te degjoj|dua të dëgjoj)\s+",
    re.IGNORECASE,
)

class MusicEngine:
    def __init__(self):
        self.api_key = os.environ.get("YOUTUBE_API_KEY", "")

    def process(self, query: str) -> dict:
        query = self._clean_query(query)
        if not query:
            return {"error": "No search query provided"}

        if not self.api_key:
            return {"error": "Music service is not configured"}

        print(f"[FalconAI Music Engine] Kërkimi për: {query}")
        try:
            r = requests.get(
                YOUTUBE_SEARCH_URL,
                params={
                    "part": "snippet",
                    "q": f"{query} audio",
                    "type": "video",
                    "videoCategoryId": "10",
                    "maxResults": 1,
                    "key": self.api_key,
                },
                timeout=10,
            )
            r.raise_for_status()
            items = r.json().get("items", [])
            if not items:
                return {"error": "No results found"}

            video_item = items[0]
            video_id = video_item["id"]["videoId"]
            title = html.unescape(video_item["snippet"]["title"])

            # Krijojmë një stream URL të qëndrueshëm që ExoPlayer e lexon përmes YouTube
            # Përdorim NewPipe/Invidious proxy ose një format direkt të audio stream
            audio_url = f"https://www.youtube.com/watch?v={video_id}"

            return {
                "text": f"Playing {title}",
                "voice_text": f"Now playing {title}",
                "data": {
                    "title": title,
                    "audio_url": audio_url,
                    "video_id": video_id,
                    "duration": 180000
                }
            }
        except Exception as e:
            print(f"[FalconAI Music Engine Error]: {e}")
            return {"error": str(e)}

    @staticmethod
    def _clean_query(query: str) -> str:
        if not query:
            return ""
        for _ in range(3):
            cleaned = FILLER_PATTERN.sub("", query).strip()
            if cleaned == query:
                break
            query = cleaned
        return re.sub(r"[\"“”]", "", query).strip(" .,!?")
