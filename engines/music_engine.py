import os
import requests

class MusicEngine:
    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY", "")

    def play(self, query: str) -> dict:
        search_query = query.lower()
        for trig in ["play", "këngë", "song", "music", "lësho", "lëshoj"]:
            search_query = search_query.replace(trig, "")
        search_query = search_query.strip()
        if not search_query:
            search_query = query

        song_title = search_query
        song_artist = "FalconAI Music"
        video_id = "6-eqUIMD1JU"

        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": f"{search_query} official music video",
            "type": "video",
            "maxResults": 1,
            "key": self.api_key
        }

        try:
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get("items", [])
                if items:
                    top_item = items[0]
                    video_id = top_item["id"]["videoId"]
                    song_title = top_item["snippet"]["title"]
                    song_artist = top_item["snippet"]["channelTitle"]
            else:
                print(f"[YouTube API Warning]: Status code {res.status_code} - {res.text}")
        except Exception as e:
            print(f"[YouTube API Error]: {e}")

        target_url = f"https://www.youtube.com/watch?v={video_id}"

        print(f"\n[FalconAI Music Engine]: Query '{query}' -> Found Video ID: {video_id} ({song_title})\n")

        return {
            "type": "audio",
            "data": {
                "query": query,
                "title": song_title,
                "artist": song_artist,
                "audio_url": target_url,
                "stream_url": target_url,
                "video_id": video_id,
                "auto_play": True,
                "falcon_ai": f"Playing {song_title} by {song_artist}."
            },
            "text": f"Playing: {song_title} - {song_artist}",
            "voice": f"Playing {song_title}.",
            "meta": {"type": "music", "intent": "play_music"}
        }
