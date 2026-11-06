import os

class MusicEngine:
    def __init__(self):
        pass

    def play(self, query: str) -> dict:
        # Nëse përdoruesi ose aplikacioni dërgon një link specifik të YouTube, e përdorim atë direkt
        if "youtube.com" in query or "youtu.be" in query:
            target_url = query.strip()
            song_title = "FalconAI Custom Stream"
            song_artist = "YouTube Source"
        else:
            # Fallback nëse është thjesht tekst
            target_url = "https://www.youtube.com/watch?v=6-eqUIMD1JU"
            song_title = "Don Xhoni / Mix"
            song_artist = "FalconAI Music"

        print(f"\n[FalconAI Music Engine]: Target URL -> {target_url}\n")

        return {
            "type": "audio",
            "data": {
                "query": query,
                "title": song_title,
                "artist": song_artist,
                "audio_url": target_url,
                "stream_url": target_url,
                "auto_play": True,
                "falcon_ai": f"Playing {song_title}."
            },
            "text": f"Playing: {song_title}",
            "voice": f"Playing {song_title}.",
            "meta": {"type": "music", "intent": "play_music"}
        }
