import os
import re
import sys
import threading
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.logger_config import setup_logger
from core.agent import Agent
from core.executor import Executor
from core.brain import FalconBrain
from core.router import Router
from core.channel_registry import CHANNELS as REGISTRY_CHANNELS
from engines.web_engine import WebEngine
from engines.music_engine import MusicEngine
from engines.weather_engine import WeatherEngine
from engines.sports_engine import SportsEngine
from engines.conversation_engine import ConversationEngine
from engines.background_engine import BackgroundEngine
from engines.watch_companion_engine import WatchCompanionEngine

try:
    from core.channel_player import ChannelPlayer
except ImportError:
    ChannelPlayer = None

try:
    from core.channel_ai import ChannelAI
except ImportError:
    ChannelAI = None

def client_ip():
    fwd = request.headers.get("X-Forwarded-For", "")
    return fwd.split(",")[0].strip() if fwd else request.remote_addr

logger = setup_logger("FalconAI.Main")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

logger.info("--- FalconAI Booting ---")

web_engine = None
music_engine = None
weather_engine = None
sports_engine = None
conversation_engine = None
background_engine = None
watch_companion = None
router = None
brain = None
agent = None
executor = None

try:
    web_engine = WebEngine()
    music_engine = MusicEngine()
    weather_engine = WeatherEngine()
    sports_engine = SportsEngine()
    conversation_engine = ConversationEngine()
    background_engine = BackgroundEngine()

    router = Router(
        conversation_engine=conversation_engine,
        music_engine=music_engine,
        web_engine=web_engine,
        weather_engine=weather_engine,
        sports_engine=sports_engine
    )

    brain = FalconBrain()

    agent = Agent(
        music_engine=music_engine,
        web_engine=web_engine,
        weather_engine=weather_engine,
        sports_engine=sports_engine,
        conversation_engine=conversation_engine
    )

    channel_ai = ChannelAI() if ChannelAI else None

    channel_player = (
        ChannelPlayer(channels=REGISTRY_CHANNELS, channel_ai=channel_ai, web_engine=web_engine)
        if ChannelPlayer else None
    )

    watch_companion = WatchCompanionEngine(conversation_engine)

    executor = Executor(
        channel_player=channel_player,
        channel_ai=channel_ai
    )

    logger.info("--- All Systems Ready (Agent, Executor, and ML Model Loaded) ---")
except Exception as e:
    logger.error(f"FATAL ERROR DURING BOOT: {str(e)}")

BACKGROUND_TRIGGERS = ["background", "sfond", "wallpaper", "backgroundin", "sfondin"]

WEATHER_PATTERN = re.compile(r"\b(weather|moti|forecast|temperatura)\b", re.IGNORECASE)
WEATHER_PREFIXES = ["weather in", "weather", "moti ne", "moti në", "moti", "forecast for", "forecast", "temperatura"]

def extract_city(clean_input: str) -> str:
    city_query = clean_input
    for prefix in WEATHER_PREFIXES:
        city_query = city_query.replace(prefix, "")
    return city_query.strip() or "Prishtina"

@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "system": "FalconAI V3",
        "version": "3.0.0"
    }), 200


@app.route('/downloads/<path:filename>')
def serve_downloaded_file(filename):
    downloads_dir = os.path.join(BASE_DIR, "downloads")
    return send_from_directory(downloads_dir, filename)


@app.route('/debug/live', methods=['GET'])
def debug_live():
    try:
        matches = sports_engine.fetch_live_matches()
        return jsonify({
            "total": len(matches),
            "matches": [
                {
                    "home": m.get("teams", {}).get("home", {}).get("name"),
                    "away": m.get("teams", {}).get("away", {}).get("name"),
                    "league": m.get("league", {}).get("name"),
                    "country": m.get("league", {}).get("country"),
                    "minute": m.get("fixture", {}).get("status", {}).get("elapsed"),
                    "score_h": m.get("goals", {}).get("home"),
                    "score_a": m.get("goals", {}).get("away"),
                }
                for m in matches
            ]
        }), 200
    except Exception as e:
        logger.error(f"Debug live error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat_request():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        if conversation_engine is None:
            return jsonify({
                "status": "error",
                "message": "Conversation engine is not initialized."
            }), 500

        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"status": "error", "message": "No text provided"}), 400

        user_text = data['text']
        user_id = data.get('user_id', "default_user")

        logger.info(f"[CHAT] User Input [{user_id}]: {user_text}")

        result = conversation_engine.chat(user_id, user_text)
        result['status'] = 'success'
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"[CHAT] Processing Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal chat processing error",
            "details": str(e)
        }), 500


@app.route('/chat/reset', methods=['POST'])
def chat_reset():
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', "default_user")
        if conversation_engine:
            conversation_engine.reset(user_id)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/watch/start', methods=['POST'])
def watch_start():
    try:
        if watch_companion is None:
            return jsonify({"status": "error", "message": "Watch Companion not initialized."}), 500

        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        channel_url = data.get('channel_url', '')
        channel_name = data.get('channel_name', '')

        if not channel_url:
            return jsonify({"status": "error", "message": "channel_url is required"}), 400

        result = watch_companion.start_session(
            session_id=user_id, channel_url=channel_url, channel_name=channel_name
        )
        result['status'] = 'success'
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"[WATCH START] Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/watch/ask', methods=['POST'])
def watch_ask():
    try:
        if watch_companion is None:
            return jsonify({"status": "error", "message": "Watch Companion not initialized."}), 500

        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        question = data.get('text', '')

        if not question:
            return jsonify({"status": "error", "message": "text is required"}), 400

        result = watch_companion.ask(session_id=user_id, user_id=user_id, question=question)
        result['status'] = 'success'
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"[WATCH ASK] Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/watch/stop', methods=['POST'])
def watch_stop():
    try:
        if watch_companion is None:
            return jsonify({"status": "error", "message": "Watch Companion not initialized."}), 500

        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')

        result = watch_companion.stop_session(user_id)
        result['status'] = 'success'
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"[WATCH STOP] Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/process', methods=['POST', 'OPTIONS'])
def process_request():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        if agent is None or executor is None or router is None:
            return jsonify({
                "status": "error",
                "message": "FalconAI core components are not initialized properly. Check boot logs."
            }), 500

        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({"status": "error", "message": "No text provided"}), 400

        user_text = data['text']
        user_id = data.get('user_id', "default_user")
        clean_input = user_text.lower().strip()

        logger.info(f"User Input [{user_id}]: {user_text}")

        if conversation_engine is not None:
            chat_result = conversation_engine.handle(user_id, user_text)
            if chat_result is not None:
                chat_result['status'] = 'success'
                return jsonify(chat_result), 200

        if background_engine and any(trig in clean_input for trig in BACKGROUND_TRIGGERS):
            try:
                bg_result = background_engine.search(user_text)
                best = bg_result.get("best_match")

                if best:
                    return jsonify({
                        "type": "background",
                        "data": {
                            "image_url": best["image_url"],
                            "page_url": best.get("page_url", ""),
                            "topic": bg_result.get("topic_used", ""),
                            "text": f"Changing background to match: {bg_result.get('topic_used')}",
                            "voice_text": f"Changing your background to {bg_result.get('topic_used')}."
                        },
                        "status": "success"
                    }), 200
                else:
                    return jsonify({
                        "type": "background",
                        "data": {
                            "image_url": "",
                            "text": "I couldn't find a matching background for that.",
                            "voice_text": "I couldn't find a matching background for that."
                        },
                        "status": "success"
                    }), 200
            except Exception as bg_err:
                logger.error(f"[Background Error]: {bg_err}")

        if WEATHER_PATTERN.search(clean_input) and weather_engine:
            city_query = extract_city(clean_input)
            try:
                try:
                    weather_res = weather_engine.get_weather(
                        city_query,
                        ip=client_ip(),
                        lat=data.get("lat"),
                        lon=data.get("lon"),
                    )
                except TypeError:
                    weather_res = weather_engine.get_weather(city_query)
                return jsonify(weather_res), 200
            except Exception as w_err:
                logger.error(f"[Weather Error]: {w_err}")

        downloads_dir = os.path.join(BASE_DIR, "downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        existing_files = set(os.listdir(downloads_dir))

        response_data = agent.handle_request(user_text, user_id)
        route_name = response_data.get("type", "unknown")

        if route_name == "video_stream":
            final_response = response_data
            if isinstance(final_response, dict) and 'status' not in final_response:
                final_response['status'] = 'success'
            return jsonify(final_response), 200

        execution_result = executor.execute_action(route_name, response_data)
        final_response = execution_result.get('response', response_data)

        if route_name == "music" or response_data.get("intent") == "play_music":
            if not isinstance(final_response, dict):
                final_response = {"text": str(final_response)}

            if "data" not in final_response:
                final_response["data"] = {}

            found_file = None
            for _ in range(35):
                time.sleep(0.2)
                current_files = set(os.listdir(downloads_dir))
                new_files = current_files - existing_files
                mp3_new = [f for f in new_files if f.endswith(".mp3")]

                if mp3_new:
                    found_file = mp3_new[0]
                    break
                else:
                    all_mp3 = [f for f in current_files if f.endswith(".mp3")]
                    if all_mp3:
                        latest_file = max([os.path.join(downloads_dir, f) for f in all_mp3], key=os.path.getctime)
                        if (time.time() - os.path.getctime(latest_file)) < 10:
                            if os.path.getsize(latest_file) > 50000:
                                found_file = os.path.basename(latest_file)
                                break

            if found_file:
                host_url = request.host_url.rstrip('/')
                final_response["data"]["stream_url"] = f"{host_url}/downloads/{found_file}"
                final_response["data"]["filename"] = found_file
            else:
                final_response["data"]["stream_url"] = ""

        if isinstance(final_response, dict) and 'status' not in final_response:
            final_response['status'] = 'success'

        return jsonify(final_response), 200

    except Exception as e:
        logger.error(f"Processing Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal processing error",
            "details": str(e)
        }), 500


def run_cli():
    print("\n" + "="*50)
    print(" FALCONAI V3 - TERMINAL TEST MODE")
    print(" Type your command or type 'exit' to quit.")
    print(" Type 'chat: <message>' to test the conversation engine.")
    print("="*50 + "\n")

    while True:
        try:
            user_input = input("FalconAI > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "dalje"):
                print("Shutting down... Goodbye!")
                os._exit(0)

            clean_input = user_input.lower()

            if conversation_engine:
                chat_result = conversation_engine.handle("cli_user", user_input)
                if chat_result is not None:
                    print(f"[FalconAI]: {chat_result.get('text')}\n")
                    continue

            if background_engine and any(trig in clean_input for trig in BACKGROUND_TRIGGERS):
                bg_result = background_engine.search(user_input)
                best = bg_result.get("best_match")
                if best:
                    print(f"[Background]: Matched '{bg_result.get('topic_used')}' -> {best['image_url']}\n")
                else:
                    print("[Background]: No matching image found.\n")
                continue

            if WEATHER_PATTERN.search(clean_input):
                city = extract_city(clean_input)

                if weather_engine:
                    try:
                        weather_res = weather_engine.get_weather(city) if hasattr(weather_engine, 'get_weather') else weather_engine.process(city)
                        msg = weather_res.get('data', {}).get('text', weather_res.get('text', str(weather_res)))
                        print(f"[Response]: {msg}\n")
                        continue
                    except Exception as w_err:
                        print(f"[Weather Error]: {w_err}")

            if agent and executor:
                downloads_dir = os.path.join(BASE_DIR, "downloads")
                os.makedirs(downloads_dir, exist_ok=True)
                existing_files = set(os.listdir(downloads_dir))

                response_data = agent.handle_request(user_input, "cli_user")
                route_name = response_data.get("type", "unknown")

                execution_result = executor.execute_action(route_name, response_data)

                final_res = execution_result.get('response', response_data)

                if isinstance(final_res, dict):
                    output_msg = final_res.get('text') or final_res.get('message') or str(final_res)
                else:
                    output_msg = str(final_res)

                print(f"[Response]: {output_msg}")

                if route_name == "music" or response_data.get("intent") == "play_music":
                    def watch_download_and_print():
                        for _ in range(30):
                            time.sleep(0.5)
                            current_files = set(os.listdir(downloads_dir))
                            new_files = current_files - existing_files
                            mp3_new = [f for f in new_files if f.endswith(".mp3")]
                            if mp3_new:
                                print(f"[Stream Link]: http://127.0.0.1:8080/downloads/{mp3_new[0]}\n")
                                break
                            elif len(current_files) > len(existing_files):
                                all_mp3 = [os.path.join(downloads_dir, f) for f in current_files if f.endswith(".mp3")]
                                if all_mp3:
                                    latest_file = max(all_mp3, key=os.path.getctime)
                                    print(f"[Stream Link]: http://127.0.0.1:8080/downloads/{os.path.basename(latest_file)}\n")
                                    break

                    threading.Thread(target=watch_download_and_print, daemon=True).start()
                else:
                    print()
            else:
                print("[Error]: Systems are not fully loaded.")
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
            break
        except Exception as e:
            print(f"[Processing Error]: {e}\n")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False))
    flask_thread.daemon = True
    flask_thread.start()

    run_cli()