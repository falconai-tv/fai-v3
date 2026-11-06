import os
import yt_dlp
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
        video_id = "Ybyen6knxSc" # Default (Don Xhoni - 100%)

        # 1. Gjejmë Video ID përmes ytmusicapi
        if self.ytmusic:
            try:
                results = self.ytmusic.search(search_query, filter="songs")
                if not results:
                    results = self.ytmusic.search(search_query)

                if results and len(results) > 0:
                    top_result = results[0]
                    vid = top_result.get('videoId')
                    if vid:
                        video_id = vid
                    song_title = top_result.get('title', song_title)
                    artists = top_result.get('artists', [])
                    if artists:
                        song_artist = artists[0].get('name', '')
            except Exception as e:
                print(f"[YTMusic Error]: {e}")

        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        stream_url = ""

        # 2. Përdorim yt-dlp me konfigurimin e klientit Android për të marrë linkun direkt të audios
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'socket_timeout': 10,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web']
                    }
                },
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                stream_url = info.get('url', '')
        except Exception as e:
            print(f"[yt-dlp Error]: {e}")

        # Fallback nëse yt-dlp dështon
        if not stream_url:
            stream_url = youtube_url

        print(f"\n[FalconAI Music Engine]: Direct Stream URL -> {stream_url}\n")

        return {
            "type": "audio",
            "data": {
                "query": query,
                "title": song_title,
                "artist": song_artist,
                "audio_url": stream_url,
                "stream_url": stream_url,
                "video_id": video_id,
                "auto_play": True,
                "falcon_ai": f"Playing {song_title} by {song_artist}."
            },
            "text": f"Playing: {song_title} - {song_artist}",
            "voice": f"Playing {song_title}.",
            "meta": {"type": "music", "intent": "play_music"}
        }
