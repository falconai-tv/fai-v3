import os
import yt_dlp
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/download_music', methods=['POST'])
def download_music():
    data = request.json
    query = data.get('query') or data.get('search_query')
    
    if not query:
        return jsonify({"error": "No search query provided"}}, 400

    print(f"[FalconAI Music Engine] Kërkimi për: {query}")

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
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
            file_path = os.path.join(DOWNLOAD_FOLDER, filename)

            print(f"[FalconAI Music Engine] U sharkua me sukses: {title} -> {file_path}")

            return jsonify({
                "status": "success",
                "title": title,
                "file_name": filename,
                "file_path": file_path,
                "stream_url": f"http://<IP_E_SERVERIT_TEND>:5000/downloads/{filename}"
            })

    except Exception as e:
        print(f"[FalconAI Music Engine Gabim]: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/downloads/<path:filename>', methods=['GET'])
def serve_downloaded_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
