import os
import re


def _has_word(text: str, words) -> bool:
    """True nëse teksti përmban një nga fjalët si fjalë të plotë
    (që 'moti' mos kapet te 'motivation', ose 'war' te 'warm'/'Warsaw')."""
    pattern = r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


WEATHER_WORDS = ["weather", "moti", "forecast", "temperatura"]

MOVIE_WORDS = [
    "movie", "movies", "film", "films", "watch something", "watch a movie",
    "watch a film", "watch films", "recommend a movie", "find a movie"
]

MUSIC_WORDS = ["play", "këngë", "kenge", "song", "songs", "music", "lësho", "lesho", "luaj"]

NEWS_WORDS = [
    "news", "latest", "war", "balkan", "tech", "sport", "sports", "business",
    "politics", "lajme", "luftë", "europe", "asia", "america", "africa"
]


class Router:
    def __init__(self, conversation_engine=None, web_engine=None, library_engine=None, music_engine=None, weather_engine=None, sports_engine=None, **kwargs):
        self.conversation_engine = conversation_engine
        self.web_engine = web_engine
        self.library_engine = library_engine
        self.music_engine = music_engine
        self.weather_engine = weather_engine
        self.sports_engine = sports_engine

    def route(self, text: str, intent: str = None, confidence: float = None, **kwargs) -> dict:
        if not text or not text.strip():
            return {
                "text": "Please write something so that I can help you.",
                "voice": "Please write something so that I can help you.",
                "meta": {"type": "error", "intent": "empty"}
            }

        cleaned = text.strip().lower()

        if cleaned in ["hello", "hi", "hey", "përshëndetje", "ckemi"]:
            response_text = "Hello! I am FalconAI, your advanced AI assistant. How can I help you today?"
            return {
                "text": response_text,
                "voice": response_text,
                "meta": {"type": "chat", "intent": "greeting"}
            }

        if _has_word(cleaned, WEATHER_WORDS):
            if self.weather_engine and hasattr(self.weather_engine, "get_weather"):
                try:
                    return self.weather_engine.get_weather(text)
                except Exception:
                    pass

        if _has_word(cleaned, MOVIE_WORDS):
            if self.web_engine and hasattr(self.web_engine, "process"):
                try:
                    movie_result = self.web_engine.process(text, intent="watch_movie")
                    if isinstance(movie_result, dict):
                        return movie_result
                except Exception:
                    pass

        if _has_word(cleaned, MUSIC_WORDS):
            if self.music_engine and hasattr(self.music_engine, "play"):
                try:
                    music_result = self.music_engine.play(text)
                    if isinstance(music_result, dict):
                        return music_result
                except Exception:
                    pass

        tried_web = False
        if intent or _has_word(cleaned, NEWS_WORDS):
            if self.web_engine and hasattr(self.web_engine, "process"):
                tried_web = True
                try:
                    result = self.web_engine.process(text, intent=intent or "general_search")
                    if isinstance(result, dict) and result.get("text"):
                        return result
                except Exception:
                    pass

        if self.conversation_engine and hasattr(self.conversation_engine, "handle"):
            try:
                user_id = kwargs.get("user_id", "default_user")
                chat_result = self.conversation_engine.handle(user_id, text)
                if isinstance(chat_result, dict):
                    return chat_result
            except Exception:
                pass

        # Kërkim i përgjithshëm në web, vetëm nëse nuk e kemi provuar tashmë më lart
        if not tried_web:
            try:
                if self.web_engine and hasattr(self.web_engine, "process"):
                    result = self.web_engine.process(text, intent=intent or "general_search")
                    if isinstance(result, dict) and result.get("text"):
                        return result
            except Exception:
                pass

        return {
            "text": f"I didn't find anything for: '{text}'. To chat with me, type 'chat: your message'.",
            "voice": "I didn't find anything. To chat with me, write chat before the message.",
            "meta": {"type": "fallback", "intent": intent}
        }
