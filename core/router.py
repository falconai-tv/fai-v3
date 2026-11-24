import os
import re

try:
    from engines.tubi_description_finder import TubiDescriptionFinder
except ImportError:
    TubiDescriptionFinder = None

def _has_word(text: str, words) -> bool:
    pattern = r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b"
    return re.search(pattern, text, re.IGNORECASE) is not None

WEATHER_WORDS = ["weather", "moti", "forecast", "temperatura"]

MOVIE_WORDS = [
    "movie", "movies", "film", "films", "watch something", "watch a movie",
    "watch a film", "watch films", "recommend a movie", "find a movie"
]

PLOT_DESCRIPTION_PHRASES = [
    "a movie where",
    "a film where",
    "movie about",
    "film about",
    "don't remember the name",
    "dont remember the name",
    "forgot the title",
    "forget the title",
    "what movie is",
    "what film is",
    "looking for a movie",
    "looking for a film",
    "sits with you",
    "days afterward",
]

MUSIC_WORDS = ["play", "këngë", "kenge", "song", "songs", "music", "lësho", "lesho", "luaj"]

NEWS_WORDS = [
    "news", "latest", "war", "balkan", "tech", "sport", "sports", "business",
    "politics", "lajme", "luftë", "europe", "asia", "america", "africa"
]


def _is_plot_description(cleaned: str) -> bool:
    if any(phrase in cleaned for phrase in PLOT_DESCRIPTION_PHRASES):
        return True
    has_media = _has_word(cleaned, ["movie", "movies", "film", "films", "cinema"])
    has_clue = _has_word(
        cleaned,
        ["where", "about", "plot", "scene", "forgot", "remember", "blind", "detective", "island", "amnesia", "tragedy", "internal"]
    )
    return has_media and has_clue


class Router:
    def __init__(
        self,
        conversation_engine=None,
        web_engine=None,
        library_engine=None,
        music_engine=None,
        weather_engine=None,
        sports_engine=None,
        tubi_description_finder=None,
        **kwargs
    ):
        self.conversation_engine = conversation_engine
        self.web_engine = web_engine
        self.library_engine = library_engine
        self.music_engine = music_engine
        self.weather_engine = weather_engine
        self.sports_engine = sports_engine
        if tubi_description_finder is not None:
            self.tubi_description_finder = tubi_description_finder
        elif TubiDescriptionFinder is not None:
            try:
                self.tubi_description_finder = TubiDescriptionFinder(timeout=4)
            except Exception:
                self.tubi_description_finder = None
        else:
            self.tubi_description_finder = None

    def _search_tubi_by_description(self, text: str) -> dict | None:
        if not self.tubi_description_finder or not hasattr(self.tubi_description_finder, "find_by_description"):
            return None
        try:
            found = self.tubi_description_finder.find_by_description(text, top_k=3)
            matches = found.get("results") or []
            if not matches:
                return {
                    "text": "I couldn't find a matching movie on Tubi from that description. Try sharing more plot details.",
                    "voice": "I couldn't find a matching movie on Tubi from that description.",
                    "data": {"results": [], "keywords": found.get("extracted_keywords", [])},
                    "meta": {"type": "movie_description_search", "intent": "watch_movie"},
                }

            top = matches[0]
            desc = (top.get("description") or "").strip()
            if len(desc) > 180:
                desc = desc[:177].rstrip() + "..."

            reply_text = (
                f"🎬 {top['title']} (Tubi TV) — {desc}"
                if desc
                else f"🎬 {top['title']} (Tubi TV)"
            )
            voice_text = f"Based on that description on Tubi, it could be {top['title']}."
            return {
                "text": reply_text,
                "voice": voice_text,
                "data": {
                    "title": top["title"],
                    "platform": top.get("platform", "Tubi TV"),
                    "url": top.get("url", ""),
                    "score": top.get("score", 0),
                    "top_match": top,
                    "results": matches,
                    "keywords": found.get("extracted_keywords", []),
                },
                "meta": {"type": "movie_description_search", "intent": "watch_movie"},
            }
        except Exception:
            return None

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

        if _is_plot_description(cleaned) or _has_word(cleaned, MOVIE_WORDS):
            tubi_res = self._search_tubi_by_description(text)
            if isinstance(tubi_res, dict):
                return tubi_res

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
