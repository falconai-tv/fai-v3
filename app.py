import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("FalconAI.App")

app = Flask(__name__)
CORS(app)

try:
    from core.smart_channel_finder import SmartChannelFinder
    smart_channel_finder = SmartChannelFinder()
    logger.info("SmartChannelFinder u ngarkua me sukses.")
except Exception as e:
    logger.error(f"Gabim gjatë ngarkimit të SmartChannelFinder: {e}")
    smart_channel_finder = None

try:
    from engines.conversation_engine import ConversationEngine
    from engines.watch_companion_engine import WatchCompanionEngine

    conversation_engine = ConversationEngine()
    watch_engine = WatchCompanionEngine(conversation_engine)
    logger.info("Engines kryesore u ngarkuan me sukses.")
except Exception as e:
    logger.error(f"Gabim gjatë ngarkimit të engines kryesore: {e}")
    conversation_engine = None
    watch_engine = None

try:
    from engines.background_engine import BackgroundEngine
    background_engine = BackgroundEngine()
    logger.info("BackgroundEngine u ngarkua me sukses.")
except Exception as e:
    logger.error(f"Gabim gjatë ngarkimit të BackgroundEngine: {e}")
    background_engine = None

try:
    from engines.weather_engine import WeatherEngine
    weather_engine = WeatherEngine()
    logger.info("WeatherEngine u ngarkua me sukses.")
except Exception as e:
    logger.error(f"Gabim gjatë ngarkimit të WeatherEngine: {e}")
    weather_engine = None

try:
    from engines.web_engine import WebEngine
    web_engine = WebEngine()
    logger.info("WebEngine u ngarkua me sukses.")
except Exception as e:
    logger.error(f"Gabim gjatë ngarkimit të WebEngine: {e}")
    web_engine = None

try:
    from engines.music_engine import MusicEngine
    yt_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    try:
        music_engine = MusicEngine(api_key=yt_key) if yt_key else MusicEngine()
    except TypeError:
        music_engine = MusicEngine()
    logger.info("MusicEngine u ngarkua me sukses.")
except Exception as e:
    logger.error(f"Gabim gjatë ngarkimit të MusicEngine: {e}")
    music_engine = None

try:
    from engines.tubi_description_finder import TubiDescriptionFinder
    tubi_finder = TubiDescriptionFinder()
    logger.info("TubiDescriptionFinder u ngarkua me sukses.")
except Exception as e:
    logger.error(f"Gabim gjatë ngarkimit të TubiDescriptionFinder: {e}")
    tubi_finder = None

try:
    from engines.tubi_semantic_scraper import AdvancedTubiSemanticEngine
    tubi_semantic = AdvancedTubiSemanticEngine()
    logger.info("AdvancedTubiSemanticEngine u ngarkua me sukses.")
except Exception as e:
    logger.error(f"Gabim gjatë ngarkimit të AdvancedTubiSemanticEngine: {e}")
    tubi_semantic = None

try:
    from engines.semantic_movie_engine import SemanticMovieEngine
    semantic_movie_engine = SemanticMovieEngine()
    logger.info("SemanticMovieEngine u ngarkua me sukses.")
except Exception as e:
    logger.error(f"Gabim gjatë ngarkimit të SemanticMovieEngine: {e}")
    semantic_movie_engine = None


def _get_client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return (request.remote_addr or "").strip()


def _normalize_movie_item(item: dict) -> dict:
    return {
        "title": item.get("title", ""),
        "platform": item.get("platform", "Tubi TV"),
        "url": item.get("url", ""),
        "description": item.get("description", ""),
        "source": item.get("source", "Tubi"),
        "score": item.get("score", item.get("match_score", 0)),
        "matched_keywords": item.get("matched_keywords", []),
        "reasoning": item.get("reasoning", item.get("matched_via_term", "")),
    }


@app.route('/', methods=['GET'])
def index():
    movie_active = any([tubi_finder, tubi_semantic, semantic_movie_engine])
    return jsonify({
        "status": "online",
        "service": "FalconAI Engine v3 API",
        "companion": "active" if watch_engine else "inactive",
        "channel_finder": "active" if smart_channel_finder else "inactive",
        "background_engine": "active" if background_engine else "inactive",
        "weather_engine": "active" if weather_engine else "inactive",
        "web_engine": "active" if web_engine else "inactive",
        "music_engine": "active" if music_engine else "inactive",
        "movie_engine": "active" if movie_active else "inactive"
    }), 200


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200


@app.route('/channel/find', methods=['POST'])
def handle_channel_find():
    if not smart_channel_finder:
        return jsonify({"status": "error", "message": "Channel finder unavailable"}), 500

    data = request.get_json(silent=True) or {}
    query = (data.get('query') or data.get('text') or '').strip()
    if not query:
        return jsonify({"status": "error", "message": "Missing 'query'"}), 400

    res = smart_channel_finder.find(query)
    return jsonify(res), 200


@app.route('/background/search', methods=['POST'])
def handle_background_search():
    if not background_engine:
        return jsonify({"status": "error", "message": "Background engine unavailable"}), 500

    data = request.get_json(silent=True) or {}
    query = (data.get('query') or data.get('text') or data.get('message') or '').strip()
    if not query:
        return jsonify({"status": "error", "message": "Missing 'query'"}), 400

    top_k = data.get('top_k', 1)
    res = background_engine.search(query, top_k=top_k)
    return jsonify(res), 200


@app.route('/weather', methods=['POST'])
def handle_weather():
    if not weather_engine:
        return jsonify({"status": "error", "message": "Weather engine unavailable"}), 500

    data = request.get_json(silent=True) or {}
    query = (
        data.get('query')
        or data.get('text')
        or data.get('message')
        or data.get('city')
        or ''
    ).strip()
    lat = data.get('lat')
    lon = data.get('lon')
    client_ip = _get_client_ip()

    res = weather_engine.process(query=query, ip=client_ip, lat=lat, lon=lon)
    return jsonify(res), 200


@app.route('/news', methods=['POST'])
def handle_news():
    if not web_engine:
        return jsonify({"status": "error", "message": "Web engine unavailable"}), 500

    data = request.get_json(silent=True) or {}
    query = (data.get('query') or data.get('text') or data.get('message') or '').strip()
    if not query:
        return jsonify({"status": "error", "message": "Missing 'query'"}), 400

    category = data.get('category')
    intent = data.get('intent')
    res = web_engine.run_news_engine(query=query, intent=intent, category=category)
    return jsonify(res), 200


@app.route('/music', methods=['GET', 'POST'])
def handle_music():
    if not music_engine:
        return jsonify({"status": "error", "message": "Music engine unavailable"}), 500

    if request.method == 'GET':
        query = (
            request.args.get('query')
            or request.args.get('q')
            or request.args.get('text')
            or ''
        ).strip()
        intent = (request.args.get('intent') or 'play_music').strip()
    else:
        data = request.get_json(silent=True) or {}
        query = (data.get('query') or data.get('text') or data.get('message') or '').strip()
        intent = (data.get('intent') or 'play_music').strip()

    if not query:
        return jsonify({"status": "error", "message": "Missing 'query'"}), 400

    try:
        if hasattr(music_engine, "process"):
            try:
                res = music_engine.process(query)
            except TypeError:
                res = music_engine.process(query=query)
        elif hasattr(music_engine, "search"):
            res = music_engine.search(query)
        elif hasattr(music_engine, "find"):
            res = music_engine.find(query)
        else:
            return jsonify({"status": "error", "message": "No matching method on MusicEngine"}), 500

        return jsonify(res), 200
    except Exception as e:
        logger.error(f"Gabim gjatë ekzekutimit të MusicEngine: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/movie/find', methods=['GET', 'POST'])
@app.route('/movie/play', methods=['POST'])
def handle_movie_find():
    if request.method == 'GET':
        query = (
            request.args.get('q')
            or request.args.get('query')
            or request.args.get('description')
            or request.args.get('text')
            or ''
        ).strip()
        top_k = int(request.args.get('top_k') or 3)
    else:
        data = request.get_json(silent=True) or {}
        query = (
            data.get('description')
            or data.get('query')
            or data.get('text')
            or data.get('message')
            or ''
        ).strip()
        top_k = int(data.get('top_k') or 3)

    if not query:
        return jsonify({"status": "error", "message": "Missing movie description/query"}), 400

    try:
        raw_results = []
        meta = {}

        if tubi_finder:
            res = tubi_finder.find_by_description(query, top_k=top_k)
            raw_results = res.get("results") or []
            if raw_results:
                meta = {
                    "engine": "TubiDescriptionFinder",
                    "extracted_keywords": res.get("extracted_keywords", []),
                }

        if not raw_results and tubi_semantic:
            sem_deep = tubi_semantic.search_tubi_deep(query, top_k=top_k)
            raw_results = sem_deep.get("results") or []
            if raw_results:
                meta = {
                    "engine": "AdvancedTubiSemanticEngine",
                    "search_terms": sem_deep.get("search_terms"),
                    "cognitive_intent_vector": sem_deep.get("cognitive_intent_vector", {}),
                }

        if not raw_results and semantic_movie_engine:
            sem_res = semantic_movie_engine.search(query, top_k=top_k)
            raw_results = sem_res.get("results") or []
            meta = {
                "engine": "SemanticMovieEngine",
                "concrete_terms_used": sem_res.get("concrete_terms_used", []),
                "note": sem_res.get("note"),
            }

        if not any([tubi_finder, tubi_semantic, semantic_movie_engine]):
            return jsonify({"status": "error", "message": "No Tubi movie engine available"}), 500

        results = [_normalize_movie_item(item) for item in raw_results[:top_k]]
        top_match = results[0] if results else None

        return jsonify({
            "status": "ok",
            "type": "movie",
            "data": top_match,
            "results": results,
            "meta": meta,
        }), 200
    except Exception as e:
        logger.error(f"Gabim te movie finder: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/chat', methods=['POST'])
def handle_chat():
    if not conversation_engine:
        return jsonify({
            "status": "error",
            "text": "Conversation engine unavailable",
            "voice": "Conversation engine unavailable",
            "meta": {"type": "chat", "error": "engine_unavailable"}
        }), 500

    data = request.get_json(silent=True) or {}
    user_text = (data.get('message') or data.get('text') or data.get('query') or '').strip()
    if not user_text:
        return jsonify({
            "status": "error",
            "text": "Missing 'message' field",
            "voice": "Please say or type a message.",
            "meta": {"type": "chat", "error": "missing_message"}
        }), 400

    user_id = (data.get('user_id') or data.get('session_id') or 'tv_user').strip()
    context = data.get('context') or {}
    current_channel = context.get('current_channel') or data.get('current_channel')

    enriched_text = user_text
    if current_channel and any(k in user_text.lower() for k in ("watching", "channel", "news", "happening", "program", "show", "shiko", "kanal")):
        enriched_text = f"[Currently watching: {current_channel}] {user_text}"

    result = conversation_engine.chat(user_id=user_id, user_text=enriched_text)
    return jsonify(result), 200


@app.route('/watch/start', methods=['POST'])
def handle_watch_start():
    if not watch_engine:
        return jsonify({"status": "error", "message": "Watch engine unavailable"}), 500

    data = request.get_json(silent=True) or {}

    session_id = data.get('session_id')
    channel_url = data.get('channel_url')
    channel_name = data.get('channel_name', 'Live Channel')
    capture_interval = data.get('capture_interval', 5.0)
    language = data.get('language', None)
    enable_audio = data.get('enable_audio', True)
    enable_vision = data.get('enable_vision', True)
    program_title = data.get('program_title', '')
    epg_info = data.get('epg_info', '')

    if not session_id or not channel_url:
        return jsonify({
            "status": "error",
            "message": "Both 'session_id' and 'channel_url' are required fields."
        }), 400

    res = watch_engine.start_session(
        session_id=session_id,
        channel_url=channel_url,
        channel_name=channel_name,
        capture_interval=capture_interval,
        language=language,
        enable_audio=enable_audio,
        enable_vision=enable_vision,
        program_title=program_title,
        epg_info=epg_info,
    )

    return jsonify(res), 200


@app.route('/watch/ask', methods=['POST'])
def handle_watch_ask():
    if not watch_engine:
        return jsonify({"status": "error", "message": "Watch engine unavailable"}), 500

    data = request.get_json(silent=True) or {}

    session_id = data.get('session_id')
    user_id = data.get('user_id', 'tv_user')

    question = data.get('text') or data.get('question')
    image_b64 = data.get('image_b64')
    program_title = data.get('program_title')
    epg_info = data.get('epg_info')

    if not session_id or not question:
        return jsonify({
            "status": "error",
            "message": "Both 'session_id' and 'text' (or 'question') are required."
        }), 400

    result = watch_engine.ask(
        session_id=session_id,
        user_id=user_id,
        question=question,
        image_b64=image_b64,
        program_title=program_title,
        epg_info=epg_info,
    )

    return jsonify(result), 200


@app.route('/watch/stop', methods=['POST'])
def handle_watch_stop():
    if not watch_engine:
        return jsonify({"status": "error", "message": "Watch engine unavailable"}), 500

    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({
            "status": "error",
            "message": "'session_id' is required to stop session."
        }), 400

    res = watch_engine.stop_session(session_id)
    return jsonify(res), 200


@app.route('/watch/status', methods=['GET', 'POST'])
def handle_watch_status():
    if not watch_engine:
        return jsonify({"status": "error", "message": "Watch engine unavailable"}), 500

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        session_id = data.get('session_id')
    else:
        session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({"status": "error", "message": "'session_id' parameter missing"}), 400

    res = watch_engine.get_status(session_id)
    return jsonify(res), 200


@app.route('/watch/debug', methods=['POST'])
def handle_watch_debug():
    """
    DIAGNOSTIC ONLY. Disabled unless DEBUG_TOKEN is set in the environment.
    Delete this route (and the env var) once the video pipeline works.
    """
    expected = os.environ.get("DEBUG_TOKEN", "")
    if not expected:
        return jsonify({"status": "error", "message": "Not found"}), 404

    if not watch_engine:
        return jsonify({"status": "error", "message": "Watch engine unavailable"}), 500

    data = request.get_json(silent=True) or {}
    if data.get("token") != expected:
        return jsonify({"status": "error", "message": "Forbidden"}), 403

    channel_url = data.get("channel_url")
    if not channel_url:
        return jsonify({"status": "error", "message": "'channel_url' is required."}), 400

    return jsonify(watch_engine.debug_grab(channel_url)), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"FalconAI v3 server po niset në portën {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
