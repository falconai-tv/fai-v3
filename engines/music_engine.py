import os
import sys
import subprocess
from ytmusicapi import YTMusic

class MusicEngine:
    def __init__(self):
        try:
            self.ytmusic = YTMusic()
        except Exception:
            self.ytmusic = None
            
        self.ffmpeg_path = "C:\\ffmpeg\\bin" if os.name == 'nt' else ""

    def play(self, query: str) -> dict:
        search_query = query.lower()
        for trig in ["play", "këngë", "song", "music", "lësho"]:
            search_query = search_query.replace(trig, "")
        search_query = search_query.strip()
        if not search_query:
            search_query = query

        song_title = search_query
        song_artist = ""
        video_url = None

        if self.ytmusic:
            try:
                results = self.ytmusic.search(search_query, filter="songs")
                if not results:
                    results = self.ytmusic.search(search_query)

                if results and len(results) > 0:
                    top_result = results[0]
                    video_id = top_result.get('videoId')
                    if video_id:
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                    song_title = top_result.get('title', song_title)
                    artists = top_result.get('artists', [])
                    if artists:
                        song_artist = artists[0].get('name', '')
            except Exception as e:
                print(f"[YTMusic Error]: {e}")

        if not video_url:
            video_url = f"ytsearch1:{search_query}"

        # Nxjerrja e linkut të transmetimit direkt përmes yt-dlp
        stream_url = ""
        try:
            ydl_opts = [
                "yt-dlp",
                "--get-url",
                "-f", "bestaudio",
                "--no-check-certificates",
                "--no-update",
                "--extractor-args", "youtube:player_client=android",
                video_url
            ]
            
            if self.ffmpeg_path and os.path.exists(self.ffmpeg_path):
                ydl_opts[1:1] = ["--ffmpeg-location", self.ffmpeg_path]

            process = subprocess.Popen(ydl_opts, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()

            if process.returncode == 0 and stdout.strip():
                lines = stdout.strip().split("\n")
                stream_url = lines[0].strip()
        except Exception as e:
            print(f"[YTDLP Stream Error]: {e}")

        # Siguri dytësore (Fallback): Nëse yt-dlp kthen bosh, përdorim vetë video_url si link bazë
        if not stream_url:
            stream_url = video_url if video_url and "http" in video_url else f"https://www.youtube.com/results?search_query={search_query}"

        print(f"\n[FalconAI Music Engine]: Generated Stream URL -> {stream_url}\n")

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
