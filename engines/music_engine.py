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

        # 1. Gjejmë Video ID përmes ytmusicapi
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

        # Fallback nëse ytmusicapi nuk kthen ID, përdorim një kërkim bazë ose ID fikse
        if not video_id:
            video_id = "Ybyen6knxSc" # Fallback te Don Xhoni - 100%

        # 2. Përdorim Piped API për të marrë linkun direkt të audios pa yt-dlp
        stream_url = ""
        try:
            piped_instances = [
                "https://pipedapi.kavin.rocks",
                "https://api.piped.video",
                "https://piped-api.garudalinux.org"
            ]
            
            for instance in piped_instances:
                try:
                    res = requests.get(f"{instance}/streams/{video_id}", timeout=5)
                    if res.status_code == 200:
                        data = res.json()
                        audio_streams = data.get("audioStreams", [])
                        if audio_streams:
                            # Zgjedhim audio stream-in cilësor
                            stream_url = audio_streams[0].get("url", "")
                            if stream_url:
                                break
                except Exception:
                    continue
        except Exception as e:
            print(f"[Piped API Error]: {e}")

        # Nëse dështojnë instancat, kthejmë linkun embed/watch si siguri
        if not stream_url:
            stream_url = f"https://www.youtube.com/watch?v={video_id}"

        print(f"\n[FalconAI Music Engine]: Final Stream URL -> {stream_url}\n")

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
