import os
import yt_dlp

class MusicEngine:
    def __init__(self):
        # Krijimi i folderit /downloads në rrënjë të projektit
        self.download_folder = os.path.join(os.getcwd(), "downloads")
        os.makedirs(self.download_folder, exist_ok=True)

    def process(self, query: str) -> dict:
        return self.download_and_get_stream(query)

    def download_and_get_stream(self, query: str) -> dict:
        if not query:
            return {"error": "No search query provided"}

        print(f"[FalconAI Music Engine] Kërkimi dhe shkarkimi për: {query}")

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(self.download_folder, '%(id)s.%(ext)s'),
            'default_search': 'ytsearch1',
            'quiet': True,
            'no_warnings': True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                
                if 'entries' in info:
                    video_info = info['entries'][0]
                else:
                    video_info = info

                video_id = video_info.get('id')
                title = video_info.get('title', 'Unknown Title')
                filename = f"{video_id}.mp3"
                file_path = os.path.join(self.download_folder, filename)

                print(f"[FalconAI Music Engine] U shkarkua me sukses: {title} -> {file_path}")

                # Lidhja dinamike që merr host-in aktual nga Render ose kërkesa
                stream_url = f"/downloads/{filename}"

                return {
                    "text": f"Playing {title}",
                    "voice_text": f"Now playing {title}",
                    "data": {
                        "title": title,
                        "file_name": filename,
                        "stream_url": stream_url
                    }
                }

        except Exception as e:
            print(f"[FalconAI Music Engine Gabim]: {str(e)}")
            return {"error": str(e)}
