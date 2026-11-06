import os
import requests
from ytmusicapi import YTMusic

class MusicEngine:
    def __init__(self):
        try:
            self.ytmusic = YTMusic()
        except Exception:
            self.ytmusic = None

    def play(self, query: str) -> dict:
        search_query = query.lower()
        for trig in ["play", "këngë", "song", "music", "lësho"]:
            search_query = search_query.replace(trig, "")
        search_query = search_query.strip()
        if not search_query:
            search_query = query

        song_title = search_query
        song_artist = ""
        video_id = None

        if self.ytmusic:
            try:
                results = self.ytmusic.search(search_query, filter="songs")
                if not results:
                    results = self.ytmusic.search(search_query)

                if results and len(results) > 0:
                    top_result = results[0]
                    video_id = top_result.get('videoId')
                    song_title = top_result.get('title', song_title)
                    artists = top_result.get('artists', [])
                    if artists:
                        song_artist = artists[0].get('name', '')
            except Exception as e:
                print(f"[YTMusic Error]: {e}")

        if not video_id:
            video_id = "Ybyen6knxSc"

        # Përdorim Invidious API si alternativë e parë, ose Cobalt API
        stream_url = ""
        youtube_watch_url = f"https://www.youtube.com/watch?v={video_id}"

        invidious_instances = [
            "https://inv.nadeko.net",
            "https://vid.priv.au",
            "https://invidious.privacyredirect.com"
        ]

        for instance in invidious_instances:
            try:
                res = requests.get(f"{instance}/api/v1/videos/{video_id}", timeout=4)
                if res.status_code == 200:
                    data = res.json()
                    adaptive_formats = data.get("adaptiveFormats", [])
                    # Kërkojmë për format audio (m4a ose webm)
                    for fmt in adaptive_formats:
                        if "audio" in fmt.get("type", ""):
                            stream_url = fmt.get("url", "")
                            if stream_url:
                                break
                    if stream_url:
                        break
            except Exception:
                continue

        # Nëse Invidious dështon, provojmë Cobalts (API publike për media streaming)
        if not stream_url:
            try:
                cobalt_res = requests.post(
                    "https://api.cobalt.tools/api/json",
                    json={"url": youtube_watch_url, "audioFormat": "mp3"},
                    headers={"Accept": "application/json", "User-Agent": "FalconAI"},
                    timeout=5
                )
                if cobalt_res.status_code == 200:
                    c_data = cobalt_res.json()
                    stream_url = c_data.get("url", "")
            except Exception as e:
                print(f"[Cobalt API Error]: {e}")

        # Fallback përfundimtar nëse gjithçka tjetër bllokohet
        if not stream_url:
            stream_url = youtube_watch_url

        print(f"\n[FalconAI Music Engine]: Final Resolved Stream URL -> {stream_url}\n")

        return {
            "type": "audio",
            "data": {
                "query": query,
                "title": song_title,
                "artist": song_artist,
                "audio_url": stream_url,
                "stream_url": stream_url,
                "auto_play": True,
                "falcon_ai": f"Playing {song_title} by {song_artist}."
            },
            "text": f"Playing: {song_title} - {song_artist}",
            "voice": f"Playing {song_title}.",
            "meta": {"type": "music", "intent": "play_music"}
        }
