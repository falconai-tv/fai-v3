import os
import re
import html
import requests

FILLER_PATTERN = re.compile(
    r"^\s*(please\s+)?(play|put on|listen to|luaj|luaje|vendos|ndiz|ndize|dua te degjoj|dua të dëgjoj)\s+",
    re.IGNORECASE,
)

# Invidious public instances të besueshme për kërkim dhe stream audio
INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://invidious.projectsegfau.lt",
    "https://vid.puffyan.us",
    "https://inv.us.projectsegfau.lt"
]

class MusicEngine:
    def __init__(self):
        pass

    def process(self, query: str) -> dict:
        query = self._clean_query(query)
        if not query:
            return {"error": "No search query provided"}

        print(f"[FalconAI Music Engine] Kërkimi për: {query}")
        
        # Provojmë instancat e Invidious deri sa njëra të kthejë rezultat të suksesshëm
        for instance in INVIDIOUS_INSTANCES:
            try:
                # 1. Kërkojmë videon
                search_url = f"{instance}/api/v1/search"
                r = requests.get(search_url, params={"q": query, "type": "video"}, timeout=8)
                if r.status_code != 200:
                    continue
                
                results = r.json()
                if not results:
                    continue
                
                video_item = results[0]
                videoId = video_item.get("videoId")
                title = html.unescape(video_item.get("title", query))
                length_sec = video_item.get("lengthSeconds", 180)

                if not videoId:
                    continue

                # 2. Marrim formatet e audios/videos për atë video direkt nga Invidious
                details_url = f"{instance}/api/v1/videos/{videoId}"
                det_res = requests.get(details_url, timeout=8)
                if det_res.status_code != 200:
                    continue
                
                det_data = det_res.json()
                adaptive_formats = det_data.get("adaptiveFormats", [])
                
                # Gjejmë url-në e audios me cilësi më të mirë
                audio_url = ""
                for fmt in adaptive_formats:
                    if "audio" in fmt.get("type", ""):
                        audio_url = fmt.get("url")
                        break
                
                # Nëse nuk gjendet te adaptive, shohim te format e thjeshta
                if not audio_url:
                    format_streams = det_data.get("formatStreams", [])
                    if format_streams:
                        audio_url = format_streams[0].get("url")

                if audio_url:
                    return {
                        "text": f"Playing {title}",
                        "voice_text": f"Now playing {title}",
                        "data": {
                            "title": title,
                            "audio_url": audio_url,
                            "video_id": videoId,
                            "duration": int(length_sec * 1000)
                        }
                    }
            except Exception as e:
                print(f"[Invidious Instance {instance} Error]: {e}")
                continue

        return {"error": "Could not retrieve audio stream from any proxy instance"}

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
