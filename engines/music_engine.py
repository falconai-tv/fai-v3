import os
import re
import html
import yt_dlp

FILLER_PATTERN = re.compile(
    r"^\s*(please\s+)?(play|put on|listen to|luaj|luaje|vendos|ndiz|ndize|dua te degjoj|dua të dëgjoj)\s+",
    re.IGNORECASE,
)

class MusicEngine:
    def __init__(self):
        pass

    def process(self, query: str) -> dict:
        query = self._clean_query(query)
        if not query:
            return {"error": "No search query provided"}

        print(f"[FalconAI Music Engine] Kërkimi për: {query}")
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'noplaylist': True,
                'quiet': True,
                'default_search': 'ytsearch1',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                if 'entries' in info:
                    entries = info['entries']
                    if not entries:
                        return {"error": "No results found"}
                    info = entries[0]

                title = html.unescape(info.get('title', query))
                audio_url = info.get('url') # Kjo është URL-ja direkte e stream-it audio (.m4a/.webm)
                video_id = info.get('id', '')
                duration_sec = info.get('duration', 180)
                
                if not audio_url:
                    return {"error": "Could not extract direct audio stream"}

                return {
                    "text": f"Playing {title}",
                    "voice_text": f"Now playing {title}",
                    "data": {
                        "title": title,
                        "audio_url": audio_url,
                        "video_id": video_id,
                        "duration": int(duration_sec * 1000)
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
